import json

import pytest
from flask import Flask

import core.api.mi_routes as mi_routes


@pytest.fixture()
def app(monkeypatch):
    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(mi_routes.mi_bp)

    def _read_json_from_request():
        return (mi_routes.request.get_json(silent=True) or {})

    monkeypatch.setattr(mi_routes, "read_json_from_request", _read_json_from_request)

    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_mi_scan_default_timeout(client, monkeypatch):
    seen = {}

    def fake_scan_devices_sync(timeout):
        seen["timeout"] = timeout
        return [{"deviceID": "d1"}]

    monkeypatch.setattr(mi_routes, "scan_devices_sync", fake_scan_devices_sync)

    resp = client.get("/mi/scan")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == [{"deviceID": "d1"}]
    assert seen["timeout"] == 5.0


def test_mi_scan_custom_timeout(client, monkeypatch):
    monkeypatch.setattr(mi_routes, "scan_devices_sync", lambda timeout: [])

    resp = client.get("/mi/scan?timeout=1.2")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == []


def test_mi_volume_requires_device_id(client):
    resp = client.get("/mi/volume")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "device_id is required"


def test_mi_volume_get_ok(client, monkeypatch):
    class FakeDev:
        def __init__(self, device_id):
            assert device_id == "d1"

        def get_volume(self):
            return 0, 22

    monkeypatch.setattr(mi_routes, "MiDevice", FakeDev)

    resp = client.get("/mi/volume?device_id=d1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == {"volume": 22}


def test_mi_volume_get_err(client, monkeypatch):
    class FakeDev:
        def __init__(self, device_id):
            pass

        def get_volume(self):
            return -1, "x"

    monkeypatch.setattr(mi_routes, "MiDevice", FakeDev)

    resp = client.get("/mi/volume?device_id=d1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "获取音量失败" in body["msg"]


def test_mi_volume_post_requires_volume(client, monkeypatch):
    monkeypatch.setattr(mi_routes, "MiDevice", lambda device_id: object())

    resp = client.post(
        "/mi/volume",
        data=json.dumps({"device_id": "d1"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "volume is required"


def test_mi_volume_post_volume_must_be_int(client, monkeypatch):
    monkeypatch.setattr(mi_routes, "MiDevice", lambda device_id: object())

    resp = client.post(
        "/mi/volume",
        data=json.dumps({"device_id": "d1", "volume": "x"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "volume must be int"


def test_mi_volume_post_range_check(client, monkeypatch):
    monkeypatch.setattr(mi_routes, "MiDevice", lambda device_id: object())

    resp = client.post(
        "/mi/volume",
        data=json.dumps({"device_id": "d1", "volume": 101}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "volume must be between 0 and 100"


def test_mi_volume_post_ok(client, monkeypatch):
    class FakeDev:
        def __init__(self, device_id):
            assert device_id == "d1"

        def set_volume(self, volume):
            assert volume == 50
            return 0, "ok"

    monkeypatch.setattr(mi_routes, "MiDevice", FakeDev)

    resp = client.post(
        "/mi/volume",
        data=json.dumps({"device_id": "d1", "volume": 50}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == {"volume": 50}


def test_mi_status_requires_device_id(client):
    resp = client.get("/mi/status")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "device_id is required"


def test_mi_status_ok(client, monkeypatch):
    class FakeDev:
        def __init__(self, device_id):
            assert device_id == "d1"

        def get_status(self):
            return 0, {"state": "play"}

    monkeypatch.setattr(mi_routes, "MiDevice", FakeDev)

    resp = client.get("/mi/status?device_id=d1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == {"state": "play"}


def test_mi_status_err_uses_error_field(client, monkeypatch):
    class FakeDev:
        def __init__(self, device_id):
            pass

        def get_status(self):
            return -1, {"error": "boom"}

    monkeypatch.setattr(mi_routes, "MiDevice", FakeDev)

    resp = client.get("/mi/status?device_id=d1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "boom"


def test_mi_status_err_non_dict_fallback_msg(client, monkeypatch):
    class FakeDev:
        def __init__(self, device_id):
            pass

        def get_status(self):
            return -1, "bad"

    monkeypatch.setattr(mi_routes, "MiDevice", FakeDev)

    resp = client.get("/mi/status?device_id=d1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "获取状态失败"


def test_mi_stop_requires_device_id(client):
    resp = client.post("/mi/stop", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "device_id is required"


def test_mi_stop_ok(client, monkeypatch):
    class FakeDev:
        def __init__(self, device_id):
            assert device_id == "d1"

        def stop(self):
            return 0, "stopped"

    monkeypatch.setattr(mi_routes, "MiDevice", FakeDev)

    resp = client.post("/mi/stop", data=json.dumps({"device_id": "d1"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["message"] == "stopped"


def test_mi_stop_exception_returns_err(client, monkeypatch):
    class FakeDev:
        def __init__(self, device_id):
            pass

        def stop(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(mi_routes, "MiDevice", FakeDev)

    resp = client.post("/mi/stop", data=json.dumps({"device_id": "d1"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "boom" in body["msg"]
