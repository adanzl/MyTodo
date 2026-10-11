"""`core.ai.ai_file` 的单元测试。

覆盖三块纯逻辑/编排行为：
- 前端传来的 `files` 解析（只认文件名，去掉路径成分）；
- Dify `/parameters` 的能力解析（决定是否放行图片）；
- `resolve_chat_files` 的编排：能力未开、张数超限、正常上传。

Dify 的上传/参数接口用 monkeypatch 挡掉，不发真实请求。
"""

import pytest

from core.ai import ai_file


@pytest.fixture(autouse=True)
def _clear_caches():
    """每个用例都从空的缓存开始，避免相互污染。"""
    ai_file._id_cache.clear()
    ai_file._capability_cache.clear()
    yield
    ai_file._id_cache.clear()
    ai_file._capability_cache.clear()


# ---------------- _parse_raw_files ----------------


def test_parse_raw_files_accepts_strings_and_objects():
    assert ai_file._parse_raw_files(["a.png", {"filename": "b.jpg"}]) == [
        "a.png",
        "b.jpg",
    ]


def test_parse_raw_files_tolerates_single_value_and_garbage():
    assert ai_file._parse_raw_files("a.png") == ["a.png"]
    assert ai_file._parse_raw_files({"filename": "a.png"}) == ["a.png"]
    assert ai_file._parse_raw_files(None) == []
    assert ai_file._parse_raw_files([]) == []
    assert ai_file._parse_raw_files(123) == []
    assert ai_file._parse_raw_files([None, "", "  ", {}]) == []


def test_parse_raw_files_strips_path_components():
    """前端只该传文件名；带上路径也归一化，防目录穿越。"""
    assert ai_file._parse_raw_files(["../../etc/passwd"]) == ["passwd"]
    assert ai_file._parse_raw_files([{"filename": "C:\\tmp\\a.png"}]) == ["a.png"]


# ---------------- image_capability ----------------


def _patch_parameters(monkeypatch, payload):
    class _Rsp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return payload

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    monkeypatch.setattr(ai_file.requests, "get", lambda *a, **k: _Rsp())


def test_capability_enabled_reads_image_limit(monkeypatch):
    _patch_parameters(
        monkeypatch,
        {
            "file_upload": {
                "enabled": True,
                "number_limits": 3,
                "image": {"enabled": True, "number_limits": 3},
            }
        },
    )

    assert ai_file.image_capability("灿灿") == (True, 3)


def test_capability_falls_back_to_top_level_numbers(monkeypatch):
    """有些版本没有 image 子对象，此时以顶层配置为准。"""
    _patch_parameters(
        monkeypatch, {"file_upload": {"enabled": True, "number_limits": 5}}
    )

    assert ai_file.image_capability("灿灿") == (True, 5)


def test_capability_disabled_when_empty_or_false(monkeypatch):
    _patch_parameters(monkeypatch, {"file_upload": {}})
    assert ai_file.image_capability("灿灿") == (False, 0)

    ai_file._capability_cache.clear()
    _patch_parameters(monkeypatch, {"file_upload": {"enabled": False}})
    assert ai_file.image_capability("灿灿") == (False, 0)


def test_capability_disabled_when_image_switch_off(monkeypatch):
    _patch_parameters(
        monkeypatch,
        {"file_upload": {"enabled": True, "image": {"enabled": False}}},
    )

    assert ai_file.image_capability("灿灿") == (False, 0)


def test_capability_is_cached(monkeypatch):
    calls = []

    class _Rsp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"file_upload": {"enabled": True, "number_limits": 3}}

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    def _get(*_a, **_k):
        calls.append(1)
        return _Rsp()

    monkeypatch.setattr(ai_file.requests, "get", _get)

    assert ai_file.image_capability("灿灿") == (True, 3)
    assert ai_file.image_capability("灿灿") == (True, 3)
    assert len(calls) == 1


def test_capability_fail_open_on_network_error(monkeypatch):
    """自检本身失败时放行，交给真实的发送结果兜底，避免误伤图片功能。"""
    import requests

    def _boom(*_a, **_k):
        raise requests.exceptions.ConnectTimeout("boom")

    monkeypatch.setattr(ai_file.requests, "get", _boom)

    assert ai_file.image_capability("灿灿") == (True, 0)


# ---------------- resolve_chat_files ----------------


def test_resolve_chat_files_returns_empty_without_files():
    assert ai_file.resolve_chat_files(None, "灿灿") == []
    assert ai_file.resolve_chat_files([], "灿灿") == []


def test_resolve_chat_files_rejects_when_capability_off(monkeypatch):
    _patch_parameters(monkeypatch, {"file_upload": {"enabled": False}})

    with pytest.raises(ai_file.AiImageError, match="未开启图片功能"):
        ai_file.resolve_chat_files(["a.png"], "灿灿")


def test_resolve_chat_files_rejects_over_limit(monkeypatch):
    _patch_parameters(
        monkeypatch,
        {"file_upload": {"enabled": True, "number_limits": 3}},
    )

    with pytest.raises(ai_file.AiImageError, match="最多只能发送 3 张"):
        ai_file.resolve_chat_files(["a.png", "b.png", "c.png", "d.png"], "灿灿")


def test_resolve_chat_files_builds_local_file_entries(monkeypatch):
    _patch_parameters(
        monkeypatch,
        {"file_upload": {"enabled": True, "number_limits": 3}},
    )
    monkeypatch.setattr(ai_file, "upload_image", lambda name, user: f"id-{name}")

    files = ai_file.resolve_chat_files(["a.png", "b.png"], "灿灿")

    assert files == [
        {
            "type": "image",
            "transfer_method": "local_file",
            "upload_file_id": "id-a.png",
        },
        {
            "type": "image",
            "transfer_method": "local_file",
            "upload_file_id": "id-b.png",
        },
    ]


# ---------------- upload_image ----------------


def test_upload_image_caches_by_user_and_filename(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(
        ai_file, "_read_pic_file", lambda name: (b"data", "image/png")
    )

    class _Rsp:
        status_code = 201

        def json(self):
            return {"id": "file-1"}

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    def _post(*_a, **_k):
        calls.append(1)
        return _Rsp()

    monkeypatch.setattr(ai_file.requests, "post", _post)

    assert ai_file.upload_image("a.png", "灿灿") == "file-1"
    assert ai_file.upload_image("a.png", "灿灿") == "file-1"
    assert len(calls) == 1

    # 不同用户各自持有自己的文件归属，不能共用缓存
    assert ai_file.upload_image("a.png", "leo") == "file-1"
    assert len(calls) == 2


def test_upload_image_reports_upstream_error(monkeypatch):
    monkeypatch.setattr(
        ai_file, "_read_pic_file", lambda name: (b"data", "image/png")
    )

    class _Rsp:
        status_code = 413

        def json(self):
            return {"code": "file_too_large", "message": ""}

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    monkeypatch.setattr(ai_file.requests, "post", lambda *a, **k: _Rsp())

    with pytest.raises(ai_file.AiImageError, match="图片太大"):
        ai_file.upload_image("a.png", "灿灿")


def test_upload_image_missing_id(monkeypatch):
    monkeypatch.setattr(
        ai_file, "_read_pic_file", lambda name: (b"data", "image/png")
    )

    class _Rsp:
        status_code = 201

        def json(self):
            return {}

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    monkeypatch.setattr(ai_file.requests, "post", lambda *a, **k: _Rsp())

    with pytest.raises(ai_file.AiImageError, match="未返回文件 id"):
        ai_file.upload_image("a.png", "灿灿")


def test_upload_image_rejects_missing_local_file(monkeypatch, tmp_path):
    """本地没有这个文件时给出可读错误，而不是把空文件传上去。"""
    monkeypatch.setattr(
        ai_file.pic_mgr, "_base_dir", str(tmp_path), raising=False
    )

    with pytest.raises(ai_file.AiImageError):
        ai_file.upload_image("nope.png", "灿灿")
