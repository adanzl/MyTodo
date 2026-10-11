"""鉴权守卫的端到端行为测试。

`core.auth_policy` 的单测只能证明策略函数本身正确；**策略是否真的接到守卫上**
（`_is_whitelisted` 是否在 `AUTH_WHITELIST_ALL_API` 之前调用它）必须走真实
WSGI 栈才能验证。这里通过 `create_app()` + `DispatcherMiddleware` 复现线上挂载
方式（app 挂在 `/api` 下），直接发请求断言结果。

背景：`AUTH_WHITELIST_ALL_API` 默认为 True，会把所有 `/api` 请求直接放行，
所以只把路径从 pic 前缀白名单里摘掉是不够的——必须像 `/getAll` 那样在函数开头
就拦下。这类失误不会有任何报错，只会静默放行，因此值得用集成测试守住。
"""

import os

import pytest
from flask import Flask
from flask_jwt_extended import create_access_token
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.test import Client

from core import create_app
from core.config import PIC_BASE_DIR, _SERVER_ROOT


@pytest.fixture(scope="module")
def api_app():
    app = create_app()
    application = DispatcherMiddleware(Flask("empty"), {"/api": app})
    return app, Client(application)


@pytest.fixture
def auth_headers(api_app):
    app, _ = api_app
    with app.app_context():
        token = create_access_token(identity={"id": 1, "name": "test"})
    return {"Authorization": f"Bearer {token}"}


def _pic_dir() -> str:
    base = PIC_BASE_DIR
    if not os.path.isabs(base):
        base = os.path.normpath(os.path.join(_SERVER_ROOT, base))
    os.makedirs(base, exist_ok=True)
    return base


def test_delete_is_rejected_without_token_and_keeps_the_file(api_app):
    """未鉴权必须 401，且**文件不能被删掉**（这正是要修的漏洞）。"""
    _, client = api_app
    name = "authguard_no_token.png"
    path = os.path.join(_pic_dir(), name)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"x" * 40)

    try:
        resp = client.post("/api/pic/delete", json={"name": name})
        assert resp.status_code == 401
        assert os.path.exists(path), "未鉴权的请求不该能删除文件"
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_delete_succeeds_with_token(api_app, auth_headers):
    """带上合法 JWT 时删除照常工作（前端 axios 会带这个头）。"""
    _, client = api_app
    name = "authguard_with_token.png"
    path = os.path.join(_pic_dir(), name)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"x" * 40)

    resp = client.post("/api/pic/delete", json={"name": name}, headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["code"] == 0
    assert not os.path.exists(path)


def test_view_still_anonymous(api_app):
    """图片查看必须保持免鉴权：`<img src>` 带不了 JWT，否则聊天里的图全裂。"""
    _, client = api_app

    resp = client.get("/api/pic/view?name=definitely_missing.png")

    assert resp.status_code != 401


def test_upload_is_rejected_without_token_and_writes_nothing(api_app):
    """未鉴权上传必须 401，且**不能落盘**（否则可被用来塞满磁盘）。"""
    import io

    _, client = api_app
    png = b"\x89PNG\r\n\x1a\n" + b"x" * 40
    name = "authguard_no_token.png"
    path = os.path.join(_pic_dir(), name)

    resp = client.post(
        "/api/pic/upload",
        data={"file": (io.BytesIO(png), name)},
        content_type="multipart/form-data",
    )

    assert resp.status_code == 401
    assert not os.path.exists(path), "未鉴权的请求不该能写入文件"


def test_upload_succeeds_with_token(api_app, auth_headers):
    """带上合法 JWT 时上传照常工作（前端 axios 会带这个头）。"""
    import io

    _, client = api_app
    png = b"\x89PNG\r\n\x1a\n" + b"x" * 40
    name = "authguard_with_token.png"
    path = os.path.join(_pic_dir(), name)

    try:
        resp = client.post(
            "/api/pic/upload",
            data={"file": (io.BytesIO(png), name)},
            content_type="multipart/form-data",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.get_json()["code"] == 0
        assert os.path.exists(path)
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_get_all_still_requires_auth(api_app):
    """既有豁免不能被削弱。"""
    _, client = api_app

    resp = client.get("/api/getAll?table=t_user_pic")

    assert resp.status_code == 401
