import json

import pytest
from flask import Flask

import core.api.bluetooth_routes as bluetooth_routes


@pytest.fixture()
def app(monkeypatch):
    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(bluetooth_routes.bluetooth_bp)

    def _read_json_from_request():
        return (bluetooth_routes.request.get_json(silent=True) or {})

    monkeypatch.setattr(bluetooth_routes, "read_json_from_request", _read_json_from_request)

    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_bluetooth_scan_default_timeout(client, monkeypatch):
    seen = {}

    def fake_scan_devices_sync(timeout):
        seen["timeout"] = timeout
        return [{"address": "AA:BB", "name": "dev"}]

    monkeypatch.setattr(bluetooth_routes.bluetooth_mgr, "scan_devices_sync", fake_scan_devices_sync)

    resp = client.get("/bluetooth/scan")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == [{"address": "AA:BB", "name": "dev"}]
    assert seen["timeout"] == 5.0


def test_bluetooth_scan_custom_timeout(client, monkeypatch):
    def fake_scan_devices_sync(timeout):
        assert timeout == 1.25
        return []

    monkeypatch.setattr(bluetooth_routes.bluetooth_mgr, "scan_devices_sync", fake_scan_devices_sync)

    resp = client.get("/bluetooth/scan?timeout=1.25")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == []


def test_bluetooth_device_requires_address(client):
    resp = client.get("/bluetooth/device")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "address" in body["msg"]


def test_bluetooth_device_ok(client, monkeypatch):
    monkeypatch.setattr(bluetooth_routes.bluetooth_mgr, "get_device", lambda address: {"address": address, "rssi": -10})

    resp = client.get("/bluetooth/device?address=AA:BB")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["address"] == "AA:BB"


def test_bluetooth_device_not_found(client, monkeypatch):
    monkeypatch.setattr(bluetooth_routes.bluetooth_mgr, "get_device", lambda address: None)

    resp = client.get("/bluetooth/device?address=AA:BB")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "device not found"


def test_bluetooth_connect_requires_address(client):
    resp = client.post("/bluetooth/connect", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "address" in body["msg"]


def test_bluetooth_connect_returns_raw_result_when_standard_format(client, monkeypatch):
    monkeypatch.setattr(bluetooth_routes.bluetooth_mgr, "connect_device_sync", lambda address: {"code": 0, "msg": "ok", "data": address})

    resp = client.post(
        "/bluetooth/connect",
        data=json.dumps({"address": "AA:BB"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body == {"code": 0, "msg": "ok", "data": "AA:BB"}


def test_bluetooth_connect_wraps_nonstandard_result(client, monkeypatch):
    monkeypatch.setattr(bluetooth_routes.bluetooth_mgr, "connect_device_sync", lambda address: True)

    resp = client.post(
        "/bluetooth/connect",
        data=json.dumps({"address": "AA:BB"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] is True


def test_bluetooth_disconnect_requires_address(client):
    resp = client.post("/bluetooth/disconnect", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "address" in body["msg"]


def test_bluetooth_disconnect_returns_raw_result_when_standard_format(client, monkeypatch):
    monkeypatch.setattr(bluetooth_routes.bluetooth_mgr, "disconnect_device_sync", lambda address: {"code": 0, "msg": "ok", "data": address})

    resp = client.post(
        "/bluetooth/disconnect",
        data=json.dumps({"address": "AA:BB"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body == {"code": 0, "msg": "ok", "data": "AA:BB"}


def test_bluetooth_disconnect_wraps_nonstandard_result(client, monkeypatch):
    monkeypatch.setattr(bluetooth_routes.bluetooth_mgr, "disconnect_device_sync", lambda address: False)

    resp = client.post(
        "/bluetooth/disconnect",
        data=json.dumps({"address": "AA:BB"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] is False


def test_bluetooth_paired_ok(client, monkeypatch):
    monkeypatch.setattr(bluetooth_routes.bluetooth_mgr, "get_paired_devices", lambda: [{"address": "AA:BB"}])

    resp = client.get("/bluetooth/paired")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == [{"address": "AA:BB"}]
