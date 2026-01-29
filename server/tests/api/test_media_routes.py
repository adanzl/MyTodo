import io
import json
import os
from unittest.mock import MagicMock

import pytest
from flask import Flask

import core.api.media_routes as media_routes


@pytest.fixture
def app(monkeypatch):
    app = Flask(__name__)
    app.config.from_object('core.config.Config')
    app.config["TESTING"] = True
    app.register_blueprint(media_routes.media_bp)

    def _read_json_from_request():
        return media_routes.request.get_json(silent=True) or {}

    monkeypatch.setattr(media_routes, "read_json_from_request", _read_json_from_request)

    return app


@pytest.fixture
def client(app):
    return app.test_client()


# region /media/getDuration


def test_media_get_duration_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda *args, **kwargs: ("/_/a.mp3", None))
    monkeypatch.setattr(media_routes, "get_media_duration", lambda path: 12.5)

    resp = client.get("/media/getDuration?path=/_/a.mp3")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["duration"] == 12.5


def test_media_get_duration_err_when_validate_fails(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda *args, **kwargs: (None, "bad path"))

    resp = client.get("/media/getDuration?path=../x")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_get_duration_err_when_get_duration_fails(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda *args, **kwargs: ("/_/a.mp3", None))
    monkeypatch.setattr(media_routes, "get_media_duration", lambda path: None)

    resp = client.get("/media/getDuration?path=/_/a.mp3")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_get_duration_permission_error(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda *args, **kwargs: ("/_/a.mp3", None))

    def raise_perm(_):
        raise PermissionError("no")

    monkeypatch.setattr(media_routes, "get_media_duration", raise_perm)

    resp = client.get("/media/getDuration?path=/_/a.mp3")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_media_get_duration_generic_exception(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda *args, **kwargs: ("/_/a.mp3", None))
    monkeypatch.setattr(media_routes, "get_media_duration", lambda path:
                        (_ for _ in ()).throw(RuntimeError("probe err")))
    resp = client.get("/media/getDuration?path=/_/a.mp3")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0
    assert "Error" in resp.get_json().get("msg", "")


# endregion

# region /media/files/<path:filepath>


def test_serve_media_file_not_found(client, monkeypatch):
    monkeypatch.setattr(media_routes.os.path, "exists", lambda p: False)
    resp = client.get("/media/files/nonexistent.mp3")
    assert resp.status_code == 404


def test_serve_media_file_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.os.path, "exists", lambda p: True)
    monkeypatch.setattr(media_routes.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(media_routes, "send_file", lambda *a, **kw: "ok")

    resp = client.get("/media/files/tmp.mp3")
    assert resp.status_code == 200


def test_serve_media_file_server_error(client, monkeypatch):
    monkeypatch.setattr(media_routes.os.path, "exists", lambda p: True)
    monkeypatch.setattr(media_routes.os.path, "isfile", lambda p: True)

    def raise_any(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(media_routes, "send_file", raise_any)

    resp = client.get("/media/files/tmp.mp3")
    assert resp.status_code == 500


def test_serve_media_file_strips_traversal_and_adds_slash(client, monkeypatch):
    """serve_media_file 会替换 ../ 并给无前导 / 的路径加 /"""
    seen_path = []

    def fake_send_file(path, *a, **kw):
        seen_path.append(path)
        return "ok"

    monkeypatch.setattr(media_routes.os.path, "exists", lambda p: True)
    monkeypatch.setattr(media_routes.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(media_routes, "send_file", fake_send_file)

    resp = client.get("/media/files/foo/../bar.mp3")
    assert resp.status_code == 200
    assert len(seen_path) == 1
    assert "../" not in seen_path[0]
    assert "foo/bar.mp3" in seen_path[0] or "bar.mp3" in seen_path[0]


# endregion

# region /media/merge/*


def test_media_merge_create_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "create_task", lambda name: (0, "ok", "tid1"))
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda tid: {"id": tid, "name": "n"})

    resp = client.post("/media/merge/create", json={"name": "n"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["id"] == "tid1"


def test_media_merge_create_err_from_mgr(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "create_task", lambda name: (-1, "fail", None))

    resp = client.post("/media/merge/create", json={"name": "n"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_merge_create_exception(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "create_task", lambda name:
                        (_ for _ in ()).throw(RuntimeError("boom")))
    resp = client.post("/media/merge/create", json={"name": "n"})
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_media_merge_upload_requires_task_id(client):
    data = {"file": (io.BytesIO(b"x"), "a.mp3")}
    resp = client.post("/media/merge/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_media_merge_upload_requires_file_part(client):
    resp = client.post("/media/merge/upload", data={"task_id": "t"}, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_media_merge_upload_requires_filename(client):
    data = {"task_id": "t", "file": (io.BytesIO(b"x"), "")}
    resp = client.post("/media/merge/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_media_merge_upload_rejects_extension(client, monkeypatch):
    monkeypatch.setattr(media_routes, "is_allowed_audio_file", lambda n: False)

    data = {"task_id": "t", "file": (io.BytesIO(b"x"), "a.txt")}
    resp = client.post("/media/merge/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_media_merge_upload_empty_filename(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda tid: {"id": tid, "files": []})
    data = {"task_id": "t", "file": (io.BytesIO(b"x"), "")}
    resp = client.post("/media/merge/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0
    assert "文件名" in resp.get_json().get("msg", "")


def test_media_merge_upload_file_type_rejected(client, monkeypatch):
    """上传文件类型校验：magic number 与扩展名均不通过时返回错误"""
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda tid: {"id": tid, "files": []})
    monkeypatch.setattr(media_routes, "get_file_type_by_magic_number", lambda f: None)
    monkeypatch.setattr(media_routes, "is_allowed_audio_file", lambda n: False)
    data = {"task_id": "t", "file": (io.BytesIO(b"x"), "a.txt")}
    resp = client.post("/media/merge/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0
    assert "不支持" in resp.get_json().get("msg", "")


def test_media_merge_upload_file_too_large(client, monkeypatch):
    """上传文件超过大小限制时返回错误"""
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda tid: {"id": tid, "files": []})
    monkeypatch.setattr(media_routes.config, "MAX_UPLOAD_FILE_SIZE", 0)
    data = {"task_id": "t", "file": (io.BytesIO(b"x"), "a.mp3")}
    resp = client.post("/media/merge/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0
    assert "大小" in resp.get_json().get("msg", "") or "限制" in resp.get_json().get("msg", "")


def test_media_merge_upload_ok(client, monkeypatch, tmp_path):
    # The config object is imported when media_routes is loaded.
    # We need to patch it directly on the module object.
    monkeypatch.setattr(media_routes.config, "MAX_UPLOAD_FILE_SIZE", 10 * 1024 * 1024, raising=False)
    monkeypatch.setattr(media_routes.config, "MAX_UPLOAD_FILE_SIZE", 10 * 1024 * 1024)
    monkeypatch.setattr(media_routes, "is_allowed_audio_file", lambda n: True)
    monkeypatch.setattr(media_routes, "ensure_directory", lambda p: os.makedirs(p, exist_ok=True))
    monkeypatch.setattr(media_routes, "get_media_task_dir", lambda tid: str(tmp_path / tid))
    monkeypatch.setattr(media_routes, "get_unique_filepath",
                        lambda task_dir, base_name, ext: os.path.join(task_dir, base_name + ext))
    monkeypatch.setattr(media_routes.os.path, "basename", os.path.basename)

    class DummyFile:
        filename = "a.mp3"

        def save(self, path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(b"x")

    monkeypatch.setattr(media_routes, "get_file_info", lambda p: {"path": p})
    monkeypatch.setattr(media_routes.audio_merge_mgr, "add_file", lambda task_id, file_path, filename: (0, "ok"))

    # Patch request.files behavior by using Flask's multipart
    data = {"task_id": "t", "file": (io.BytesIO(b"x"), "a.mp3")}
    resp = client.post("/media/merge/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert resp.get_json()["code"] == 0


def test_media_merge_add_file_by_path_happy_path(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda *a, **kw: ("/_/a.mp3", None))
    monkeypatch.setattr(media_routes.os.path, "exists", lambda p: True)
    monkeypatch.setattr(media_routes.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(media_routes, "is_allowed_audio_file", lambda n: True)
    monkeypatch.setattr(media_routes.audio_merge_mgr, "add_file", lambda task_id, file_path, filename: (0, "ok"))
    monkeypatch.setattr(media_routes, "get_file_info", lambda p: {"path": p})

    resp = client.post("/media/merge/addFileByPath", json={"task_id": "t", "file_path": "/_/a.mp3"})
    assert resp.status_code == 200
    assert resp.get_json()["code"] == 0


def test_media_merge_add_file_by_path_mgr_err(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda *a, **kw: ("/_/a.mp3", None))
    monkeypatch.setattr(media_routes.os.path, "exists", lambda p: True)
    monkeypatch.setattr(media_routes.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(media_routes, "is_allowed_audio_file", lambda n: True)
    monkeypatch.setattr(media_routes.audio_merge_mgr, "add_file", lambda *a, **kw: (-1, "bad"))

    resp = client.post("/media/merge/addFileByPath", json={"task_id": "t", "file_path": "/_/a.mp3"})
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_media_merge_add_file_by_path_invalid_path(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda *a, **kw: (None, "bad path"))
    resp = client.post("/media/merge/addFileByPath", json={"task_id": "t", "file_path": "x"})
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_media_merge_delete_file_requires_params(client):
    resp = client.post("/media/merge/deleteFile", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_merge_delete_file_bad_index(client):
    resp = client.post("/media/merge/deleteFile", json={"task_id": "t", "file_index": "x"})
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_media_merge_delete_file_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "remove_file", lambda task_id, file_index: (0, "removed"))

    resp = client.post("/media/merge/deleteFile", json={"task_id": "tid", "file_index": 1})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_media_merge_delete_file_mgr_err(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "remove_file", lambda task_id, file_index: (-1, "bad"))

    resp = client.post("/media/merge/deleteFile", json={"task_id": "tid", "file_index": 1})
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_media_merge_reorder_files_requires_list(client):
    resp = client.post("/media/merge/reorderFiles", json={"task_id": "tid", "file_indices": "not-a-list"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_merge_reorder_files_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "reorder_files", lambda task_id, file_indices: (0, "ok"))
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda task_id: {"id": task_id, "files": [1, 2]})

    resp = client.post("/media/merge/reorderFiles", json={"task_id": "tid", "file_indices": [1, 0]})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["id"] == "tid"


def test_media_merge_reorder_files_mgr_err(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "reorder_files", lambda task_id, file_indices: (-1, "bad"))
    resp = client.post("/media/merge/reorderFiles", json={"task_id": "tid", "file_indices": [1]})
    assert resp.get_json()["code"] != 0


def test_media_merge_reorder_files_missing_task_id(client):
    resp = client.post("/media/merge/reorderFiles", json={"file_indices": [0]})
    assert resp.get_json()["code"] != 0
    assert "task_id" in resp.get_json().get("msg", "")


def test_media_merge_reorder_files_missing_file_indices(client):
    resp = client.post("/media/merge/reorderFiles", json={"task_id": "tid"})
    assert resp.get_json()["code"] != 0
    assert "file_indices" in resp.get_json().get("msg", "")


def test_media_merge_add_file_by_path_not_exists(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda p: ("/abs/path.mp3", None))
    monkeypatch.setattr(media_routes.os.path, "exists", lambda p: False)
    resp = client.post("/media/merge/addFileByPath", json={"task_id": "t", "file_path": "/x.mp3"})
    assert resp.get_json()["code"] != 0
    assert "不存在" in resp.get_json().get("msg", "")


def test_media_merge_add_file_by_path_not_file(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda p: ("/abs/dir", None))
    monkeypatch.setattr(media_routes.os.path, "exists", lambda p: True)
    monkeypatch.setattr(media_routes.os.path, "isfile", lambda p: False)
    resp = client.post("/media/merge/addFileByPath", json={"task_id": "t", "file_path": "/dir"})
    assert resp.get_json()["code"] != 0
    assert "不是文件" in resp.get_json().get("msg", "")


def test_media_merge_add_file_by_path_add_fails(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda p: ("/abs/a.mp3", None))
    monkeypatch.setattr(media_routes.os.path, "exists", lambda p: True)
    monkeypatch.setattr(media_routes.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(media_routes, "is_allowed_audio_file", lambda n: True)
    monkeypatch.setattr(media_routes.audio_merge_mgr, "add_file", lambda tid, path, name: (-1, "add failed"))
    resp = client.post("/media/merge/addFileByPath", json={"task_id": "t", "file_path": "/abs/a.mp3"})
    assert resp.get_json()["code"] != 0
    assert "add failed" in resp.get_json().get("msg", "")


def test_media_merge_delete_file_exception(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "remove_file", lambda tid, idx: (_ for _ in ()).throw(ValueError("mgr err")))
    resp = client.post("/media/merge/deleteFile", json={"task_id": "t", "file_index": 0})
    assert resp.get_json()["code"] != 0
    assert "删除" in resp.get_json().get("msg", "")


def test_media_merge_start_requires_task_id(client):
    resp = client.post("/media/merge/start", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_merge_start_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "start_task", lambda task_id: (0, "ok"))
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda task_id: {
        "id": task_id,
        "status": "processing"
    })

    resp = client.post("/media/merge/start", json={"task_id": "tid"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_media_merge_start_mgr_err(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "start_task", lambda task_id: (-1, "bad"))
    resp = client.post("/media/merge/start", json={"task_id": "tid"})
    assert resp.get_json()["code"] != 0


def test_media_merge_get_task_not_found(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda task_id: None)

    resp = client.post("/media/merge/get", json={"task_id": "tid"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_merge_get_task_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda task_id: {"id": task_id})
    resp = client.post("/media/merge/get", json={"task_id": "tid"})
    assert resp.get_json()["code"] == 0


def test_media_merge_list_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "list_tasks", lambda: [{"id": "a"}])

    resp = client.get("/media/merge/list")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["tasks"] == [{"id": "a"}]


def test_media_merge_list_exception(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "list_tasks", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    resp = client.get("/media/merge/list")
    assert resp.get_json()["code"] != 0


def test_media_merge_delete_task_ok_and_err(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "delete_task", lambda task_id: (0, "ok"))
    resp = client.post("/media/merge/delete", json={"task_id": "t"})
    assert resp.get_json()["code"] == 0

    monkeypatch.setattr(media_routes.audio_merge_mgr, "delete_task", lambda task_id: (-1, "bad"))
    resp = client.post("/media/merge/delete", json={"task_id": "t"})
    assert resp.get_json()["code"] != 0


def test_media_merge_download_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda tid: {
        "status": "success",
        "result_file": "/_/f.mp3"
    })
    monkeypatch.setattr(media_routes.os.path, "exists", lambda p: True)
    monkeypatch.setattr(media_routes, "send_file", lambda *a, **kw: "ok")

    resp = client.get("/media/merge/download?task_id=t1")
    assert resp.status_code == 200


def test_media_merge_download_validations(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda tid: None)
    resp = client.get("/media/merge/download?task_id=t1")
    assert resp.json["code"] != 0

    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda tid: {"status": "pending"})
    resp = client.get("/media/merge/download?task_id=t1")
    assert resp.json["code"] != 0

    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda tid: {
        "status": "success",
        "result_file": "/_/f.mp3"
    })
    monkeypatch.setattr(media_routes.os.path, "exists", lambda p: False)
    resp = client.get("/media/merge/download?task_id=t1")
    assert resp.json["code"] != 0


def test_media_merge_download_exception(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda tid:
                        (_ for _ in ()).throw(RuntimeError("boom")))
    resp = client.get("/media/merge/download?task_id=t1")
    assert resp.get_json()["code"] != 0


def test_media_merge_save_success(client, monkeypatch, tmp_path):
    monkeypatch.setattr(media_routes,
                        "validate_and_normalize_path",
                        lambda p, must_be_file=False: (str(tmp_path), None))
    monkeypatch.setattr(media_routes.os.path, "exists", lambda p: True)
    monkeypatch.setattr(media_routes.os.path, "isdir", lambda p: True)

    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda tid: {
        "status": "success",
        "result_file": "/_/f.mp3"
    })
    monkeypatch.setattr(media_routes.os.path, "exists", lambda p: True)
    monkeypatch.setattr(media_routes, "get_unique_filepath",
                        lambda target_path, task_id, ext: os.path.join(target_path, task_id + ext))
    monkeypatch.setattr(media_routes.shutil, "copy2", lambda src, dst: None)

    resp = client.post("/media/merge/save", json={"task_id": "t", "target_path": str(tmp_path)})
    assert resp.status_code == 200
    assert resp.get_json()["code"] == 0


def test_media_merge_save_validations(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda *a, **kw: (None, "bad path"))
    resp = client.post("/media/merge/save", json={"task_id": "t", "target_path": "p"})
    assert resp.json["code"] != 0


# endregion

# region /media/convert/*


def test_media_convert_list_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_convert_mgr, "get_task_list", lambda: [{"id": "c"}])

    resp = client.get("/media/convert/list")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_media_convert_list_exception(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_convert_mgr, "get_task_list", lambda:
                        (_ for _ in ()).throw(RuntimeError("boom")))
    resp = client.get("/media/convert/list")
    assert resp.get_json()["code"] != 0


def test_media_convert_create_ok(client, monkeypatch):
    monkeypatch.setattr(
        media_routes.audio_convert_mgr,
        "create_task",
        lambda name, output_dir=None, overwrite=None: (0, "ok", "cid"),
    )
    monkeypatch.setattr(media_routes.audio_convert_mgr, "get_task", lambda task_id: {"id": task_id})

    resp = client.post("/media/convert/create", json={"name": "n", "output_dir": "mp3", "overwrite": True})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["id"] == "cid"


def test_media_convert_create_mgr_err(client, monkeypatch):
    monkeypatch.setattr(
        media_routes.audio_convert_mgr,
        "create_task",
        lambda name, output_dir=None, overwrite=None: (-1, "bad", None),
    )
    resp = client.post("/media/convert/create", json={"name": "n"})
    assert resp.get_json()["code"] != 0


def test_media_convert_get_requires_task_id(client):
    resp = client.post("/media/convert/get", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_convert_get_ok_and_not_found(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_convert_mgr, "get_task", lambda task_id: None)
    resp = client.post("/media/convert/get", json={"task_id": "cid"})
    assert resp.get_json()["code"] != 0

    monkeypatch.setattr(media_routes.audio_convert_mgr, "get_task", lambda task_id: {"id": task_id})
    resp = client.post("/media/convert/get", json={"task_id": "cid"})
    assert resp.get_json()["code"] == 0


def test_media_convert_delete_ok_and_mgr_err(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_convert_mgr, "delete_task", lambda task_id: (0, "ok"))

    resp = client.post("/media/convert/delete", json={"task_id": "cid"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0

    monkeypatch.setattr(media_routes.audio_convert_mgr, "delete_task", lambda task_id: (-1, "bad"))
    resp = client.post("/media/convert/delete", json={"task_id": "cid"})
    assert resp.get_json()["code"] != 0


def test_media_convert_update_requires_any_field(client):
    resp = client.post("/media/convert/update", json={"task_id": "cid"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_convert_update_directory_validation_and_mgr_err(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda *a, **kw: (None, "bad"))

    resp = client.post("/media/convert/update", json={"task_id": "cid", "directory": "x"})
    assert resp.get_json()["code"] != 0

    monkeypatch.setattr(media_routes,
                        "validate_and_normalize_path",
                        lambda directory, must_be_file=False: ("/_/d", None))
    monkeypatch.setattr(media_routes.audio_convert_mgr, "update_task", lambda task_id, **kwargs: (-1, "bad"))
    resp = client.post("/media/convert/update", json={"task_id": "cid", "directory": "/_/d"})
    assert resp.get_json()["code"] != 0


def test_media_convert_update_ok(monkeypatch, client):
    monkeypatch.setattr(media_routes,
                        "validate_and_normalize_path",
                        lambda directory, must_be_file=False: ("/_/d", None))
    monkeypatch.setattr(media_routes.audio_convert_mgr, "update_task", lambda task_id, **kwargs: (0, "ok"))
    monkeypatch.setattr(media_routes.audio_convert_mgr, "get_task", lambda task_id: {
        "id": task_id,
        "directory": "/_/d"
    })

    resp = client.post("/media/convert/update", json={"task_id": "cid", "directory": "/_/d"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_media_convert_start_ok_and_mgr_err(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_convert_mgr, "start_task", lambda task_id: (0, "ok"))
    monkeypatch.setattr(media_routes.audio_convert_mgr, "get_task", lambda task_id: {
        "id": task_id,
        "status": "processing"
    })

    resp = client.post("/media/convert/start", json={"task_id": "cid"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0

    monkeypatch.setattr(media_routes.audio_convert_mgr, "start_task", lambda task_id: (-1, "bad"))
    resp = client.post("/media/convert/start", json={"task_id": "cid"})
    assert resp.get_json()["code"] != 0


# endregion
