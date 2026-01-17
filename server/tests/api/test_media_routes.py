import json

import pytest
from flask import Flask

import core.api.media_routes as media_routes


@pytest.fixture()
def app(monkeypatch):
    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(media_routes.media_bp)

    def _read_json_from_request():
        return (media_routes.request.get_json(silent=True) or {})

    monkeypatch.setattr(media_routes, "read_json_from_request", _read_json_from_request)

    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_media_get_duration_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda *args, **kwargs: ("/mnt/a.mp3", None))
    monkeypatch.setattr(media_routes, "get_media_duration", lambda path: 12.5)

    resp = client.get("/media/getDuration?path=/mnt/a.mp3")
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


def test_media_merge_create_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "create_task", lambda name: (0, "ok", "tid1"))
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda tid: {"id": tid, "name": "n"})

    resp = client.post("/media/merge/create", data=json.dumps({"name": "n"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["id"] == "tid1"


def test_media_merge_create_err_from_mgr(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "create_task", lambda name: (-1, "fail", None))

    resp = client.post("/media/merge/create", data=json.dumps({"name": "n"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_merge_delete_file_requires_params(client):
    resp = client.post("/media/merge/deleteFile", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_merge_delete_file_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "remove_file", lambda task_id, file_index: (0, "removed"))

    resp = client.post(
        "/media/merge/deleteFile",
        data=json.dumps({"task_id": "tid", "file_index": 1}),
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_media_merge_reorder_files_requires_list(client):
    resp = client.post(
        "/media/merge/reorderFiles",
        data=json.dumps({"task_id": "tid", "file_indices": "not-a-list"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_merge_reorder_files_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "reorder_files", lambda task_id, file_indices: (0, "ok"))
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda task_id: {"id": task_id, "files": [1, 2]})

    resp = client.post(
        "/media/merge/reorderFiles",
        data=json.dumps({"task_id": "tid", "file_indices": [1, 0]}),
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["id"] == "tid"


def test_media_merge_start_requires_task_id(client):
    resp = client.post("/media/merge/start", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_merge_start_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "start_task", lambda task_id: (0, "ok"))
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda task_id: {"id": task_id, "status": "processing"})

    resp = client.post("/media/merge/start", data=json.dumps({"task_id": "tid"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_media_merge_get_task_not_found(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "get_task", lambda task_id: None)

    resp = client.post("/media/merge/get", data=json.dumps({"task_id": "tid"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_merge_list_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_merge_mgr, "list_tasks", lambda: [{"id": "a"}])

    resp = client.get("/media/merge/list")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["tasks"] == [{"id": "a"}]


def test_media_convert_list_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_convert_mgr, "get_task_list", lambda: [{"id": "c"}])

    resp = client.get("/media/convert/list")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_media_convert_create_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_convert_mgr, "create_task", lambda name, output_dir=None, overwrite=None: (0, "ok", "cid"))
    monkeypatch.setattr(media_routes.audio_convert_mgr, "get_task", lambda task_id: {"id": task_id})

    resp = client.post(
        "/media/convert/create",
        data=json.dumps({"name": "n", "output_dir": "mp3", "overwrite": True}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["id"] == "cid"


def test_media_convert_get_requires_task_id(client):
    resp = client.post("/media/convert/get", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_convert_delete_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_convert_mgr, "delete_task", lambda task_id: (0, "ok"))

    resp = client.post("/media/convert/delete", data=json.dumps({"task_id": "cid"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_media_convert_update_requires_any_field(client):
    resp = client.post(
        "/media/convert/update",
        data=json.dumps({"task_id": "cid"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_media_convert_update_ok(monkeypatch, client):
    monkeypatch.setattr(media_routes, "validate_and_normalize_path", lambda directory, must_be_file=False: ("/mnt/d", None))
    monkeypatch.setattr(media_routes.audio_convert_mgr, "update_task", lambda task_id, **kwargs: (0, "ok"))
    monkeypatch.setattr(media_routes.audio_convert_mgr, "get_task", lambda task_id: {"id": task_id, "directory": "/mnt/d"})

    resp = client.post(
        "/media/convert/update",
        data=json.dumps({"task_id": "cid", "directory": "/mnt/d"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_media_convert_start_ok(client, monkeypatch):
    monkeypatch.setattr(media_routes.audio_convert_mgr, "start_task", lambda task_id: (0, "ok"))
    monkeypatch.setattr(media_routes.audio_convert_mgr, "get_task", lambda task_id: {"id": task_id, "status": "processing"})

    resp = client.post("/media/convert/start", data=json.dumps({"task_id": "cid"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
