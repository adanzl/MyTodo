import io
import os
from unittest.mock import MagicMock

import pytest
from flask import Flask

import core.api.pic_routes as pic_routes


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(pic_routes, 'db_mgr', MagicMock())
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(pic_routes.pic_bp, url_prefix='/pic')
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# =========== viewPic（数据库图片）==========
def test_view_pic_requires_id(client):
    resp = client.get('/pic/viewPic')
    assert resp.status_code == 400


def test_view_pic_invalid_id(client):
    resp = client.get('/pic/viewPic?id=abc')
    assert resp.status_code == 400


def test_view_pic_ok_and_not_found(client, monkeypatch):
    monkeypatch.setattr(pic_routes, "render_template", lambda *a, **kw: "ok")

    pic_routes.db_mgr.get_data_idx.return_value = {"code": 0, "data": "img"}
    resp = client.get('/pic/viewPic?id=1')
    assert resp.status_code == 200

    pic_routes.db_mgr.get_data_idx.return_value = {"code": -1}
    resp = client.get('/pic/viewPic?id=1')
    assert resp.status_code == 404


# =========== upload ==========
def test_upload_requires_file(client):
    resp = client.post('/pic/upload')
    data = resp.get_json()
    assert data["code"] != 0
    assert "未找到" in data["msg"]


def test_upload_requires_filename(client):
    data = {"file": (io.BytesIO(b"\xff\xd8\xff"), "")}
    resp = client.post('/pic/upload', data=data)
    body = resp.get_json()
    assert body["code"] != 0


def test_upload_invalid_extension(client):
    data = {"file": (io.BytesIO(b"x"), "a.txt")}
    resp = client.post('/pic/upload', data=data)
    body = resp.get_json()
    assert body["code"] != 0
    assert "不允许" in body["msg"]


def test_upload_ok(client, monkeypatch, tmp_path):
    monkeypatch.setattr(pic_routes, "PIC_BASE_DIR", str(tmp_path))
    data = {"file": (io.BytesIO(b"\xff\xd8\xff"), "test.jpg")}
    resp = client.post('/pic/upload', data=data)
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["filename"] == "test.jpg"
    assert os.path.isfile(os.path.join(tmp_path, "test.jpg"))


# =========== delete ==========
def test_delete_requires_name(client):
    resp = client.post('/pic/delete')
    body = resp.get_json()
    assert body["code"] != 0
    assert "缺少" in body["msg"]


def test_delete_invalid_extension(client):
    resp = client.post('/pic/delete', json={"name": "a.txt"})
    body = resp.get_json()
    assert body["code"] != 0


def test_delete_not_found(client, monkeypatch):
    monkeypatch.setattr(pic_routes, "PIC_BASE_DIR", "/nonexistent")
    resp = client.post('/pic/delete', json={"name": "noexist.jpg"})
    body = resp.get_json()
    assert body["code"] != 0
    assert "不存在" in body["msg"]


def test_delete_ok(client, monkeypatch, tmp_path):
    monkeypatch.setattr(pic_routes, "PIC_BASE_DIR", str(tmp_path))
    fpath = tmp_path / "delme.jpg"
    fpath.write_bytes(b"x")
    resp = client.post('/pic/delete', json={"name": "delme.jpg"})
    body = resp.get_json()
    assert body["code"] == 0
    assert not fpath.exists()


# =========== view（文件系统图片）==========
def test_view_requires_name(client):
    resp = client.get('/pic/view')
    assert resp.status_code == 400


def test_view_invalid_extension(client):
    resp = client.get('/pic/view?name=a.txt')
    assert resp.status_code == 400


def test_view_not_found(client, monkeypatch):
    monkeypatch.setattr(pic_routes, "PIC_BASE_DIR", "/nonexistent")
    resp = client.get('/pic/view?name=noexist.jpg')
    assert resp.status_code == 404


def test_view_ok(client, monkeypatch, tmp_path):
    monkeypatch.setattr(pic_routes, "PIC_BASE_DIR", str(tmp_path))
    fpath = tmp_path / "show.jpg"
    fpath.write_bytes(b"\xff\xd8\xff")
    resp = client.get('/pic/view?name=show.jpg')
    assert resp.status_code == 200
    assert resp.data == b"\xff\xd8\xff"
