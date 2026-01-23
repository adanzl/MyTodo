import pytest
from flask import Flask

import core.api.tts_routes as tr


@pytest.fixture
def app(monkeypatch, tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(tr.tts_bp)

    # Mock tts_mgr methods to avoid filesystem/threads
    monkeypatch.setattr(tr.tts_mgr, "create_task", lambda **kw: (0, "任务创建成功", "t1"))
    monkeypatch.setattr(tr.tts_mgr, "update_task", lambda **kw: (0, "任务更新成功"))
    monkeypatch.setattr(tr.tts_mgr, "start_task", lambda task_id: (0, "TTS 任务已启动"))
    monkeypatch.setattr(tr.tts_mgr, "stop_task", lambda task_id: (0, "已请求停止任务"))
    monkeypatch.setattr(tr.tts_mgr, "delete_task", lambda task_id: (0, "任务删除成功"))
    monkeypatch.setattr(tr.tts_mgr, "get_task", lambda task_id: {"task_id": task_id, "name": "n", "status": "pending"})
    monkeypatch.setattr(tr.tts_mgr, "list_tasks", lambda: [{"task_id": "t1"}])

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_create_tts_task_ok(client):
    resp = client.post('/tts/create', json={"text": "hello"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == 0
    assert data["data"]["task_id"] == "t1"


def test_update_tts_task_ok(client):
    resp = client.post('/tts/update', json={"task_id": "t1", "text": "x"})
    assert resp.status_code == 200
    assert resp.get_json()["code"] == 0


def test_start_stop_delete_ok(client):
    resp = client.post('/tts/start', json={"task_id": "t1"})
    assert resp.get_json()["code"] == 0

    resp = client.post('/tts/stop', json={"task_id": "t1"})
    assert resp.get_json()["code"] == 0

    resp = client.post('/tts/delete', json={"task_id": "t1"})
    assert resp.get_json()["code"] == 0


def test_get_tts_task_requires_task_id(client):
    resp = client.get('/tts/get')
    assert resp.get_json()["code"] == -1


def test_get_tts_task_ok(client):
    resp = client.get('/tts/get?task_id=t1')
    assert resp.get_json()["code"] == 0
    assert resp.get_json()["data"]["task_id"] == "t1"


def test_list_tts_tasks_ok(client):
    resp = client.get('/tts/list')
    assert resp.get_json()["code"] == 0
    assert isinstance(resp.get_json()["data"], list)
