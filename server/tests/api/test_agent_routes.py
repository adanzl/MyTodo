import json

import pytest
from flask import Flask

import core.api.agent_routes as agent_routes


@pytest.fixture()
def app(monkeypatch):
    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(agent_routes.agent_bp)

    # Make read_json_from_request deterministic for tests.
    def _read_json_from_request():
        return (agent_routes.request.get_json(silent=True) or {})

    monkeypatch.setattr(agent_routes, "read_json_from_request", _read_json_from_request)

    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_agent_heartbeat_ok_calls_mgr(client, monkeypatch):
    calls = {}

    def fake_handle_heartbeat(*, client_ip, address, name, actions):
        calls["client_ip"] = client_ip
        calls["address"] = address
        calls["name"] = name
        calls["actions"] = actions

    monkeypatch.setattr(agent_routes.agent_mgr, "handle_heartbeat", fake_handle_heartbeat)

    resp = client.post(
        "/agent/heartbeat",
        data=json.dumps({
            "address": "http://1.2.3.4:8000",
            "name": "dev",
            "actions": ["a"]
        }),
        content_type="application/json",
        headers={"X-Real-IP": "10.0.0.9"},
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert calls["client_ip"] == "10.0.0.9"
    assert calls["address"] == "http://1.2.3.4:8000"
    assert calls["name"] == "dev"
    assert calls["actions"] == ["a"]


def test_agent_heartbeat_requires_address(client, monkeypatch):
    monkeypatch.setattr(agent_routes.agent_mgr, "handle_heartbeat", lambda **kwargs: None)

    resp = client.post(
        "/agent/heartbeat",
        data=json.dumps({"name": "dev"}),
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "address" in body["msg"]


def test_agent_event_ok(client, monkeypatch):

    def fake_handle_event(*, client_ip, key, value, action):
        assert client_ip == "1.1.1.1"
        assert key == "k"
        assert value == "v"
        assert action == "act"
        return 0, "ok"

    monkeypatch.setattr(agent_routes.agent_mgr, "handle_event", fake_handle_event)

    resp = client.post(
        "/agent/event",
        data=json.dumps({
            "key": "k",
            "value": "v",
            "action": "act"
        }),
        content_type="application/json",
        headers={"X-Forwarded-For": "1.1.1.1, 2.2.2.2"},
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_agent_event_error_code_propagates(client, monkeypatch):
    monkeypatch.setattr(agent_routes.agent_mgr, "handle_event", lambda **kwargs: (-1, "bad"))

    resp = client.post(
        "/agent/event",
        data=json.dumps({"key": "k"}),
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "bad"


def test_agent_list_formats_is_online_and_last_heartbeat(monkeypatch, client):
    fake_devices = {
        "addr1": {
            "address": "addr1",
            "name": "n1",
            "heartbeat_time": 1000,
            "actions": ["a"],
            "register_time": 1
        },
        "addr2": {
            "address": "addr2",
            "name": "n2",
            "heartbeat_time": 0,
            "actions": [],
            "register_time": 2
        },
    }

    monkeypatch.setattr(agent_routes.agent_mgr, "get_all_agents", lambda: fake_devices)
    monkeypatch.setattr(agent_routes.time, "time", lambda: 1020)

    resp = client.get("/agent/list")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0

    data = body["data"]
    assert isinstance(data, list)

    # addr1: 20 seconds ago -> online
    d1 = next(x for x in data if x["address"] == "addr1")
    assert d1["last_heartbeat_ago"] == 20
    assert d1["is_online"] is True

    # addr2: heartbeat_time=0 -> offline, last_heartbeat_ago=-1
    d2 = next(x for x in data if x["address"] == "addr2")
    assert d2["last_heartbeat_ago"] == -1
    assert d2["is_online"] is False


def test_agent_mock_ok_returns_data(client, monkeypatch):

    class FakeAgent:

        def mock(self, *, action, key, value):
            assert action == "act"
            assert key == "k"
            assert value == "v"
            return {"code": 0, "data": {"x": 1}}

    monkeypatch.setattr(agent_routes.agent_mgr, "get_agent", lambda agent_id: FakeAgent()
                        if agent_id == "id1" else None)

    resp = client.post(
        "/agent/mock",
        data=json.dumps({
            "agent_id": "id1",
            "action": "act",
            "key": "k",
            "value": "v"
        }),
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == {"x": 1}


def test_agent_mock_requires_agent_id_and_action(client):
    resp = client.post(
        "/agent/mock",
        data=json.dumps({"agent_id": "id1"}),
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_agent_mock_agent_not_found(client, monkeypatch):
    monkeypatch.setattr(agent_routes.agent_mgr, "get_agent", lambda agent_id: None)

    resp = client.post(
        "/agent/mock",
        data=json.dumps({
            "agent_id": "id404",
            "action": "act"
        }),
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "agent not found" in body["msg"]


def test_agent_mock_returns_err_when_agent_returns_nonzero(client, monkeypatch):

    class FakeAgent:

        def mock(self, *, action, key, value):
            return {"code": -1, "msg": "nope"}

    monkeypatch.setattr(agent_routes.agent_mgr, "get_agent", lambda agent_id: FakeAgent())

    resp = client.post(
        "/agent/mock",
        data=json.dumps({
            "agent_id": "id1",
            "action": "act"
        }),
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert body["msg"] == "nope"
