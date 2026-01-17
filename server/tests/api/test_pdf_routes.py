import io
import json

import pytest
from flask import Flask

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
    def fake_upload_file(file, filename):
        assert filename == "a.pdf"
        return 0, "ok", {"filename": filename}

    monkeypatch.setattr(pdf_routes.pdf_mgr, "upload_file", fake_upload_file)

    data = {"file": (io.BytesIO(b"%PDF-1.4"), "a.pdf")}
    resp = client.post("/pdf/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["filename"] == "a.pdf"


def test_pdf_decrypt_requires_task_id(client):
    resp = client.post("/pdf/decrypt", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_pdf_decrypt_ok(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "decrypt", lambda task_id, password: (0, "submitted"))

    resp = client.post(
        "/pdf/decrypt",
        data=json.dumps({"task_id": "a.pdf", "password": "p"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["message"] == "submitted"


def test_pdf_decrypt_err_from_mgr(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "decrypt", lambda task_id, password: (-1, "bad"))

    resp = client.post(
        "/pdf/decrypt",
        data=json.dumps({"task_id": "a.pdf"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "bad"


def test_pdf_task_status_ok(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "get_task_status", lambda task_id: (0, "ok", {"id": task_id, "status": "done"}))

    resp = client.get("/pdf/task/a.pdf")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["id"] == "a.pdf"


def test_pdf_list_ok(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "list", lambda: {"uploaded": [], "unlocked": []})

    resp = client.get("/pdf/list")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


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


def test_pdf_delete_requires_task_id(client):
    resp = client.post("/pdf/delete", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_pdf_delete_ok(client, monkeypatch):
    monkeypatch.setattr(pdf_routes.pdf_mgr, "delete", lambda task_id: (0, "deleted"))

    resp = client.post("/pdf/delete", data=json.dumps({"task_id": "a.pdf"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["message"] == "deleted"
