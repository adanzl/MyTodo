import json

import pytest
from flask import Flask

import core.api.playlist_routes as playlist_routes


@pytest.fixture()
def app(monkeypatch):
    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(playlist_routes.playlist_bp)

    def _read_json_from_request():
        return (playlist_routes.request.get_json(silent=True) or {})

    monkeypatch.setattr(playlist_routes, "read_json_from_request", _read_json_from_request)

    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_playlist_get_all_when_id_missing(client, monkeypatch):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "get_playlist", lambda pid: {"all": True}
                        if pid is None else None)

    resp = client.get("/playlist/get")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == {"all": True}


@pytest.mark.parametrize("pid", ["", "None", "null"])
def test_playlist_get_all_when_id_is_emptyish(client, monkeypatch, pid):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "get_playlist", lambda x: {"all": True} if x is None else None)

    resp = client.get(f"/playlist/get?id={pid}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == {"all": True}


def test_playlist_get_single_not_found_returns_err(client, monkeypatch):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "get_playlist", lambda pid: None)

    resp = client.get("/playlist/get?id=p1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "未找到标识为" in body["msg"]


def test_playlist_get_single_ok(client, monkeypatch):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "get_playlist", lambda pid: {"id": pid})

    resp = client.get("/playlist/get?id=p1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == {"id": "p1"}


def test_playlist_update_requires_body(client):
    resp = client.post("/playlist/update", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_playlist_update_requires_id(client):
    resp = client.post("/playlist/update", data=json.dumps({"name": "x"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "id" in body["msg"]


def test_playlist_update_ok(client, monkeypatch):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "update_single_playlist", lambda data: 0)

    resp = client.post("/playlist/update", data=json.dumps({"id": "p1"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_playlist_update_err_when_mgr_fails(client, monkeypatch):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "update_single_playlist", lambda data: -1)

    resp = client.post("/playlist/update", data=json.dumps({"id": "p1"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_playlist_update_all_requires_body(client):
    resp = client.post("/playlist/updateAll", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_playlist_update_all_ok(client, monkeypatch):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "save_playlist", lambda data: 0)

    resp = client.post("/playlist/updateAll", data=json.dumps({"p1": {"id": "p1"}}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_playlist_update_all_err_when_mgr_fails(client, monkeypatch):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "save_playlist", lambda data: -1)

    resp = client.post("/playlist/updateAll", data=json.dumps({"p1": {"id": "p1"}}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


@pytest.mark.parametrize(
    "path, mgr_method, ok_msg_part",
    [
        ("/playlist/play", "play", "播放播放列表"),
        ("/playlist/playNext", "play_next", "播放下一首"),
        ("/playlist/playPre", "play_pre", "播放上一首"),
        ("/playlist/stop", "stop", "停止播放"),
    ],
)
def test_playlist_actions_require_id(client, path, mgr_method, ok_msg_part):
    resp = client.post(path, data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "id is required" in body["msg"]


@pytest.mark.parametrize(
    "path, mgr_method",
    [
        ("/playlist/play", "play"),
        ("/playlist/playNext", "play_next"),
        ("/playlist/playPre", "play_pre"),
        ("/playlist/stop", "stop"),
    ],
)
def test_playlist_actions_ok(client, monkeypatch, path, mgr_method):
    monkeypatch.setattr(playlist_routes.playlist_mgr, mgr_method, lambda pid: (0, "ok"))

    resp = client.post(path, data=json.dumps({"id": "p1"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


@pytest.mark.parametrize(
    "path, mgr_method",
    [
        ("/playlist/play", "play"),
        ("/playlist/playNext", "play_next"),
        ("/playlist/playPre", "play_pre"),
        ("/playlist/stop", "stop"),
    ],
)
def test_playlist_actions_err_when_mgr_fails(client, monkeypatch, path, mgr_method):
    monkeypatch.setattr(playlist_routes.playlist_mgr, mgr_method, lambda pid: (-1, "no"))

    resp = client.post(path, data=json.dumps({"id": "p1"}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0


def test_playlist_reload_ok(client, monkeypatch):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "reload", lambda: 0)

    resp = client.post("/playlist/reload", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0


def test_playlist_reload_err(client, monkeypatch):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "reload", lambda: -1)

    resp = client.post("/playlist/reload", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] != 0
    assert "重新加载" in body["msg"]


def test_playlist_update_exception(client, monkeypatch):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "update_single_playlist", lambda data:
                        (_ for _ in ()).throw(ValueError("mgr err")))
    resp = client.post("/playlist/update", data=json.dumps({"id": "p1"}), content_type="application/json")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_playlist_update_all_exception(client, monkeypatch):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "save_playlist", lambda data:
                        (_ for _ in ()).throw(RuntimeError("save err")))
    resp = client.post("/playlist/updateAll", data=json.dumps({"p1": {}}), content_type="application/json")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_playlist_play_exception(client, monkeypatch):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "play", lambda pid: (_ for _ in ()).throw(OSError("play err")))
    resp = client.post("/playlist/play", data=json.dumps({"id": "p1"}), content_type="application/json")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0


def test_playlist_reload_exception(client, monkeypatch):
    monkeypatch.setattr(playlist_routes.playlist_mgr, "reload", lambda: (_ for _ in ()).throw(ValueError("reload err")))
    resp = client.post("/playlist/reload", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 200
    assert resp.get_json()["code"] != 0
