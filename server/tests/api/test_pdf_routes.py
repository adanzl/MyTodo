import io
import json

import pytest
from flask import Flask
from werkzeug.exceptions import RequestEntityTooLarge

import core.api.pdf_routes as pdf_routes


@pytest.fixture()
def app(monkeypatch):
    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(pdf_routes.pdf_bp)

    def _read_json_from_request():
        return (pdf_routes.request.get_json(silent=True) or {})

    monkeypatch.setattr(pdf_routes, "read_json_from_request", _read_json_from_request)

    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_pdf_upload_requires_file(client):
    resp = client.post("/pdf/upload")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_pdf_upload_requires_filename(client):
    data = {"file": (io.BytesIO(b"%PDF"), "")}
    resp = client.post("/pdf/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_pdf_upload_ok(client, monkeypatch):

    def fake_create_task(file, filename):
        assert filename == "a.pdf"
        return 0, "ok", "a.pdf"

    monkeypatch.setattr(pdf_routes.pdf_mgr, "create_task", fake_create_task)
    monkeypatch.setattr(pdf_routes.pdf_mgr, "get_task", lambda task_id: {"filename": task_id, "name": task_id})

    data = {"file": (io.BytesIO(b"%PDF-1.4"), "a.pdf")}
    resp = client.post("/pdf/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["name"] == "a.pdf"


def test_pdf_upload_handles_request_entity_too_large(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "create_task", lambda f, fn: (_ for _ in ()).throw(RequestEntityTooLarge()))
    data = {"file": (io.BytesIO(b"%PDF-1.4"), "a.pdf")}
    resp = client.post("/pdf/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "文件太大" in body["msg"]


def test_pdf_upload_handles_generic_exception(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "create_task", lambda f, fn: (_ for _ in ()).throw(Exception("boom")))
    data = {"file": (io.BytesIO(b"%PDF-1.4"), "a.pdf")}
    resp = client.post("/pdf/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "boom" in body["msg"]


def test_pdf_decrypt_requires_task_id(client):
    resp = client.post("/pdf/decrypt", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_pdf_decrypt_ok(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "start_task", lambda task_id, password: (0, "submitted"))

    resp = client.post(
        "/pdf/decrypt",
        data=json.dumps({
            "task_id": "a.pdf",
            "password": "p"
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["message"] == "submitted"


def test_pdf_decrypt_err_from_mgr(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "start_task", lambda task_id, password: (-1, "bad"))

    resp = client.post(
        "/pdf/decrypt",
        data=json.dumps({"task_id": "a.pdf"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "bad"


def test_pdf_decrypt_handles_exception(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "start_task", lambda task_id, password:
                        (_ for _ in ()).throw(Exception("boom")))
    resp = client.post(
        "/pdf/decrypt",
        data=json.dumps({"task_id": "a.pdf"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "boom" in body["msg"]


def test_pdf_task_status_ok(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "get_task", lambda task_id: {"id": task_id, "status": "done"})

    resp = client.get("/pdf/task/a.pdf")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["id"] == "a.pdf"


def test_pdf_task_status_err_from_mgr(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "get_task", lambda task_id: None)
    resp = client.get("/pdf/task/a.pdf")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "任务不存在"


def test_pdf_task_status_handles_exception(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "get_task", lambda task_id: (_ for _ in ()).throw(Exception("boom")))
    resp = client.get("/pdf/task/a.pdf")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "boom" in body["msg"]


def test_pdf_list_ok(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "list_tasks", lambda: [])

    resp = client.get("/pdf/list")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_pdf_list_handles_exception(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "list_tasks", lambda: (_ for _ in ()).throw(Exception("boom")))
    resp = client.get("/pdf/list")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "boom" in body["msg"]


def test_pdf_download_invalid_type(client):
    resp = client.get("/pdf/download/a.pdf?type=bad")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_pdf_download_file_not_exists(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.os.path, "exists", lambda p: False)

    resp = client.get("/pdf/download/a.pdf?type=unlocked")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_pdf_download_ok_unlocked(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.os.path, "exists", lambda p: True)
    monkeypatch.setattr(pdf_routes, "send_file", lambda *args, **kwargs: "ok")
    resp = client.get("/pdf/download/a.pdf?type=unlocked")
    assert resp.status_code == 200


def test_pdf_download_ok_uploaded(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.os.path, "exists", lambda p: True)
    monkeypatch.setattr(pdf_routes, "send_file", lambda *args, **kwargs: "ok")
    resp = client.get("/pdf/download/a.pdf?type=uploaded")
    assert resp.status_code == 200


def test_pdf_download_handles_exception(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.os.path, "exists", lambda p: (_ for _ in ()).throw(Exception("boom")))
    resp = client.get("/pdf/download/a.pdf?type=unlocked")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "boom" in body["msg"]


def test_pdf_delete_requires_task_id(client):
    resp = client.post("/pdf/delete", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_pdf_delete_ok(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "delete_task", lambda task_id: (0, "deleted"))

    resp = client.post("/pdf/delete", data=json.dumps({"task_id": "a.pdf"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["message"] == "deleted"


def test_pdf_delete_err_from_mgr(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "delete_task", lambda task_id: (-1, "bad"))
    resp = client.post("/pdf/delete", data=json.dumps({"task_id": "a.pdf"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "bad"


def test_pdf_delete_handles_exception(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "delete_task", lambda task_id: (_ for _ in ()).throw(Exception("boom")))
    resp = client.post("/pdf/delete", data=json.dumps({"task_id": "a.pdf"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "boom" in body["msg"]
