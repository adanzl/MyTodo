import json

import pytest
from flask import Flask

import core.api.dlna_routes as dlna_routes


@pytest.fixture()
def app(monkeypatch):
    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(dlna_routes.dlna_bp)

    def _read_json_from_request():
        return (dlna_routes.request.get_json(silent=True) or {})

    monkeypatch.setattr(dlna_routes, "read_json_from_request", _read_json_from_request)

    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_dlna_scan_default_timeout(client, monkeypatch):
    seen = {}

    def fake_scan_devices_sync(timeout):
        seen["timeout"] = timeout
        return [{"location": "http://dev"}]

    monkeypatch.setattr(dlna_routes, "scan_devices_sync", fake_scan_devices_sync)

    resp = client.get("/dlna/scan")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == [{"location": "http://dev"}]
    assert seen["timeout"] == 5.0


def test_dlna_scan_custom_timeout(client, monkeypatch):
    monkeypatch.setattr(dlna_routes, "scan_devices_sync", lambda timeout: [])

    resp = client.get("/dlna/scan?timeout=1.5")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == []


def test_dlna_volume_requires_location(client):
    resp = client.get("/dlna/volume")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "location is required"


def test_dlna_volume_get_ok(client, monkeypatch):

    class FakeDev:

        def __init__(self, location):
            assert location == "loc"

        def get_volume(self):
            return 0, 33

    monkeypatch.setattr(dlna_routes, "DlnaDev", FakeDev)

    resp = client.get("/dlna/volume?location=loc")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == {"volume": 33}


def test_dlna_volume_get_err(client, monkeypatch):

    class FakeDev:

        def __init__(self, location):
            pass

        def get_volume(self):
            return -1, None

    monkeypatch.setattr(dlna_routes, "DlnaDev", FakeDev)

    resp = client.get("/dlna/volume?location=loc")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_dlna_volume_post_requires_volume(client, monkeypatch):
    monkeypatch.setattr(dlna_routes, "DlnaDev", lambda location: object())

    resp = client.post("/dlna/volume", data=json.dumps({"location": "loc"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "volume is required"


def test_dlna_volume_post_volume_must_be_int(client, monkeypatch):
    monkeypatch.setattr(dlna_routes, "DlnaDev", lambda location: object())

    resp = client.post(
        "/dlna/volume",
        data=json.dumps({
            "location": "loc",
            "volume": "x"
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "volume must be int"


def test_dlna_volume_post_range_check(client, monkeypatch):
    monkeypatch.setattr(dlna_routes, "DlnaDev", lambda location: object())

    resp = client.post(
        "/dlna/volume",
        data=json.dumps({
            "location": "loc",
            "volume": 101
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "volume must be between 0 and 100"


def test_dlna_volume_post_ok(client, monkeypatch):

    class FakeDev:

        def __init__(self, location):
            assert location == "loc"

        def set_volume(self, v):
            assert v == 50
            return 0, "ok"

    monkeypatch.setattr(dlna_routes, "DlnaDev", FakeDev)

    resp = client.post(
        "/dlna/volume",
        data=json.dumps({
            "location": "loc",
            "volume": 50
        }),
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == {"volume": 50}


def test_dlna_stop_requires_location(client):
    resp = client.post("/dlna/stop", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "location is required"


def test_dlna_stop_ok(client, monkeypatch):

    class FakeDev:

        def __init__(self, location):
            assert location == "loc"

        def stop(self):
            return 0, "stopped"

    monkeypatch.setattr(dlna_routes, "DlnaDev", FakeDev)

    resp = client.post("/dlna/stop", data=json.dumps({"location": "loc"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["message"] == "stopped"


def test_dlna_scan_exception(client, monkeypatch):
    monkeypatch.setattr(dlna_routes, "scan_devices_sync", lambda t: (_ for _ in ()).throw(RuntimeError("scan err")))
    resp = client.get("/dlna/scan")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_dlna_volume_get_failure(client, monkeypatch):

    class FakeDev:

        def __init__(self, location):
            pass

        def get_volume(self):
            return -1, None

    monkeypatch.setattr(dlna_routes, "DlnaDev", FakeDev)
    resp = client.get("/dlna/volume?location=loc")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0
    assert "音量" in resp.get_json().get("msg", "")


def test_dlna_stop_failure(client, monkeypatch):

    class FakeDev:

        def __init__(self, location):
            pass

        def stop(self):
            return -1, "device busy"

    monkeypatch.setattr(dlna_routes, "DlnaDev", FakeDev)
    resp = client.post("/dlna/stop", data=json.dumps({"location": "loc"}), content_type="application/json")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_dlna_stop_exception(client, monkeypatch):
    monkeypatch.setattr(dlna_routes, "DlnaDev", lambda location: (_ for _ in ()).throw(ConnectionError("dlna err")))
    resp = client.post("/dlna/stop", data=json.dumps({"location": "loc"}), content_type="application/json")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0
