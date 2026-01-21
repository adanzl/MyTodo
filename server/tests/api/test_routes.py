import builtins
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from flask import Flask

import core.api.routes as routes


@pytest.fixture
def app(monkeypatch):
    """Create a Flask app instance for testing."""

    # Mock managers before app creation to prevent real connections
    monkeypatch.setattr(routes, 'db_mgr', MagicMock())
    monkeypatch.setattr(routes, 'rds_mgr', MagicMock())
    monkeypatch.setattr(routes, 'AILocal', MagicMock())

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(routes.api_bp)

    def _read_json_from_request():
        return routes.request.get_json(silent=True) or {}

    monkeypatch.setattr(routes, "read_json_from_request", _read_json_from_request)

    yield app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


def test_natapp_ok(client, monkeypatch):

    class DummyFile:

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return "hello"

    monkeypatch.setattr(builtins, "open", lambda *a, **kw: DummyFile())

    resp = client.get('/natapp')
    assert resp.status_code == 200
    assert "Natapp Log" in resp.get_data(as_text=True)
    assert "hello" in resp.get_data(as_text=True)


def test_server_log_ok(client, monkeypatch):

    class DummyFile:

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def readlines(self):
            return ["a\n", "b\n"]

    monkeypatch.setattr(builtins, "open", lambda *a, **kw: DummyFile())
    monkeypatch.setattr(routes, "render_template", lambda *a, **kw: "ok")

    resp = client.get('/log')
    assert resp.status_code == 200


def test_write_log_ok_and_exception(client, monkeypatch):
    resp = client.post('/write_log', data=b"hi")
    assert resp.status_code == 200

    class BadReq:

        def get_data(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(routes, "request", BadReq())
    resp = client.post('/write_log', data=b"hi")
    assert resp.status_code == 200


def test_view_pic_requires_id(client):
    resp = client.get('/viewPic')
    assert resp.status_code == 400


def test_view_pic_invalid_id(client, monkeypatch):
    resp = client.get('/viewPic?id=abc')
    assert resp.status_code == 400


def test_view_pic_ok_and_not_found(client, monkeypatch):
    monkeypatch.setattr(routes, "render_template", lambda *a, **kw: "ok")

    routes.db_mgr.get_data_idx.return_value = {"code": 0, "data": "img"}
    resp = client.get('/viewPic?id=1')
    assert resp.status_code == 200

    routes.db_mgr.get_data_idx.return_value = {"code": -1}
    resp = client.get('/viewPic?id=1')
    assert resp.status_code == 404


def test_get_save_ok(client, monkeypatch):
    routes.db_mgr.get_save.return_value = {"code": 0, "data": {"id": 1, "content": "test"}}

    response = client.get('/getSave?id=1')
    assert response.status_code == 200
    data = response.get_json()
    assert data["code"] == 0
    assert data["data"]["content"] == "test"
    routes.db_mgr.get_save.assert_called_once_with(1)


def test_get_save_invalid_id(client):
    response = client.get('/getSave?id=abc')
    assert response.status_code == 200
    data = response.get_json()
    assert data["code"] == -1
    assert "must be int" in data["msg"]


def test_set_save_ok(client, monkeypatch):
    routes.db_mgr.set_save.return_value = {"code": 0}

    payload = {"id": 1, "user": "testuser", "data": {"key": "value"}}
    response = client.post('/setSave', json=payload)

    assert response.status_code == 200
    assert response.get_json()["code"] == 0
    routes.db_mgr.set_save.assert_called_once_with(1, "testuser", '{"key": "value"}')


def test_get_all_fields_split(client, monkeypatch):
    routes.db_mgr.get_list.return_value = {"code": 0, "data": {"data": []}}

    resp = client.get('/getAll?table=t&pageNum=1&pageSize=2&fields=a,b&conditions=' + json.dumps({"x": 1}))
    assert resp.status_code == 200
    routes.db_mgr.get_list.assert_called_once()
    args, kwargs = routes.db_mgr.get_list.call_args
    assert args[0] == 't'
    assert args[1] == 1
    assert args[2] == 2
    assert args[3] == ['a', 'b']
    assert args[4] == {"x": 1}


def test_get_data_fields_none_uses_data_idx(client, monkeypatch):
    routes.db_mgr.get_data_idx.return_value = {"code": 0}

    resp = client.get('/getData?table=t&id=1&idx=2')
    assert resp.status_code == 200
    routes.db_mgr.get_data_idx.assert_called_once_with('t', 1, 2)


def test_get_data_fields_non_none_uses_get_data(client, monkeypatch):
    routes.db_mgr.get_data.return_value = {"code": 0}

    resp = client.get('/getData?table=t&id=1&fields=a')
    assert resp.status_code == 200
    routes.db_mgr.get_data.assert_called_once_with('t', 1, 'a')


def test_set_data_ok(client, monkeypatch):
    routes.db_mgr.set_data.return_value = {"code": 0}
    resp = client.post('/setData', json={"table": "t", "data": []})
    assert resp.status_code == 200
    routes.db_mgr.set_data.assert_called_once_with('t', [])


def test_del_data_ok(client, monkeypatch):
    routes.db_mgr.del_data.return_value = {"code": 0}
    resp = client.post('/delData', json={"table": "t", "id": 1})
    assert resp.status_code == 200
    routes.db_mgr.del_data.assert_called_once_with('t', 1)


def test_query_no_sql(client):
    resp = client.post('/query', json={})
    assert resp.json["code"] == -1


def test_get_rds_data_ok_and_exception(client, monkeypatch):
    routes.rds_mgr.get_str.return_value = "v"
    resp = client.get('/getRdsData?table=t&id=1')
    assert resp.status_code == 200
    assert resp.json["code"] == 0

    routes.rds_mgr.get_str.side_effect = RuntimeError("boom")
    resp = client.get('/getRdsData?table=t&id=1')
    assert resp.status_code == 200
    assert resp.json["code"] == -1


def test_get_rds_list_total_zero(client, monkeypatch):
    routes.rds_mgr.llen.return_value = 0
    resp = client.get('/getRdsList?key=k')
    assert resp.status_code == 200
    assert resp.json["data"]["totalCount"] == 0


def test_get_rds_list_total_nonzero(client, monkeypatch):
    routes.rds_mgr.llen.return_value = 5
    routes.rds_mgr.lrange.return_value = ['a']
    resp = client.get('/getRdsList?key=k&pageSize=2&startId=-1')
    assert resp.status_code == 200
    assert resp.json["code"] == 0
    assert resp.json["data"]["totalCount"] == 5


def test_get_rds_list_exception(client, monkeypatch):
    routes.rds_mgr.llen.side_effect = RuntimeError("boom")
    resp = client.get('/getRdsList?key=k')
    assert resp.status_code == 200
    assert resp.json["code"] == -1


def test_set_rds_data_ok_and_exception(client):
    resp = client.post('/setRdsData', json={"table": "t", "data": {"id": "1", "value": "v"}})
    assert resp.status_code == 200
    assert resp.json["code"] == 0

    routes.rds_mgr.set.side_effect = RuntimeError("boom")
    resp = client.post('/setRdsData', json={"table": "t", "data": {"id": "1", "value": "v"}})
    assert resp.status_code == 200
    assert resp.json["code"] == -1


def test_chat_messages_ok_and_exception(client, monkeypatch):
    routes.AILocal.get_chat_messages.return_value = []
    resp = client.get('/chatMessages?conversation_id=c')
    assert resp.status_code == 200
    assert resp.json["code"] == 0

    routes.AILocal.get_chat_messages.side_effect = RuntimeError("boom")
    resp = client.get('/chatMessages?conversation_id=c')
    assert resp.status_code == 200
    assert resp.json["code"] == -1


def test_route_index_ok(client, monkeypatch):
    monkeypatch.setattr(routes, "render_template", lambda *a, **kw: "ok")
    resp = client.get('/index')
    assert resp.status_code == 200


def test_add_score_ok_and_invalid_user(client, monkeypatch):
    routes.db_mgr.add_score.return_value = {"code": 0}
    resp = client.post('/addScore', json={"user": 1, "value": 1, "action": "a", "msg": "m"})
    assert resp.status_code == 200

    resp = client.post('/addScore', json={"user": "x"})
    assert resp.status_code == 200
    assert resp.json["code"] == -1


def test_do_lottery_paths(client, monkeypatch):
    # user not found
    routes.db_mgr.get_data.return_value = {"code": -1}
    resp = client.post('/doLottery', json={"user_id": 1, "cate_id": 1})
    assert resp.status_code == 200
    assert resp.json["msg"] == "User not found"

    # cate_id==0 no lottery data
    routes.db_mgr.get_data.return_value = {"code": 0, "data": {"score": 100}}
    routes.rds_mgr.get_str.return_value = None
    resp = client.post('/doLottery', json={"user_id": 1, "cate_id": 0})
    assert resp.status_code == 200
    assert resp.json["msg"] == "No lottery data"

    # cate_id==0 insufficient score
    routes.rds_mgr.get_str.return_value = json.dumps({"fee": 10})
    routes.db_mgr.get_data.return_value = {"code": 0, "data": {"score": 0}}
    resp = client.post('/doLottery', json={"user_id": 1, "cate_id": 0})
    assert resp.json["msg"] == "Not enough score"

    # cate_id!=0 category not found
    routes.db_mgr.get_data.side_effect = [
        {
            "code": 0,
            "data": {
                "score": 100
            }
        },
        {
            "code": -1
        },
    ]
    resp = client.post('/doLottery', json={"user_id": 1, "cate_id": 2})
    assert resp.json["msg"] == "Category not found"

    # cate_id!=0 no gifts
    routes.db_mgr.get_data.side_effect = [
        {
            "code": 0,
            "data": {
                "score": 100
            }
        },
        {
            "code": 0,
            "data": {
                "cost": 10
            }
        },
    ]
    routes.db_mgr.get_list.return_value = {"code": 0, "data": {"data": []}}
    resp = client.post('/doLottery', json={"user_id": 1, "cate_id": 2})
    assert resp.json["msg"] == "No available gifts"

    # exception path
    routes.db_mgr.get_data.side_effect = RuntimeError("boom")
    resp = client.post('/doLottery', json={"user_id": 1, "cate_id": 2})
    assert resp.json["code"] == -1


def test_add_rds_list_ok_and_missing_params(client, monkeypatch):
    resp = client.post('/addRdsList', json={"key": "k", "value": "v"})
    assert resp.status_code == 200
    assert resp.json["code"] == 0

    resp = client.post('/addRdsList', json={"key": "k"})
    assert resp.status_code == 200
    assert resp.json["code"] == -1


def test_list_directory_more_branches(client, monkeypatch):
    monkeypatch.setattr(routes.config, 'DEFAULT_BASE_DIR', '/mnt')

    monkeypatch.setattr(routes.os.path, 'abspath', lambda p: p)
    monkeypatch.setattr(routes.os.path, 'isabs', lambda p: True)
    monkeypatch.setattr(routes.os.path, 'exists', lambda p: True)

    def fake_access(path, mode):
        return True

    monkeypatch.setattr(routes.os, 'access', fake_access)

    monkeypatch.setattr(routes.os, 'listdir', lambda p: ['track 2.mp3', 'track 10.mp3', 'a.txt', 'dir1'])

    class Stat:
        st_size = 1
        st_mtime = 2

    monkeypatch.setattr(routes.os, 'stat', lambda p: Stat())

    monkeypatch.setattr(routes.os.path, 'isdir', lambda p: p.endswith('dir1'))

    resp = client.get('/listDirectory?path=/mnt/music&extensions=.mp3')
    assert resp.status_code == 200
    assert resp.json["code"] == 0
    # ensure filter applied: only dirs + mp3
    names = [x['name'] for x in resp.json['data']]
    assert 'a.txt' not in names


def test_list_directory_permission_denied(client, monkeypatch):
    monkeypatch.setattr(routes.config, 'DEFAULT_BASE_DIR', '/mnt')
    monkeypatch.setattr(routes.os.path, 'abspath', lambda p: p)
    monkeypatch.setattr(routes.os.path, 'isabs', lambda p: True)
    monkeypatch.setattr(routes.os.path, 'exists', lambda p: True)

    monkeypatch.setattr(routes.os, 'listdir', lambda p: [])

    def fake_access(path, mode):
        return False

    monkeypatch.setattr(routes.os, 'access', fake_access)
    resp = client.get('/listDirectory?path=/mnt/music')
    assert resp.status_code == 200
    assert resp.json['code'] == -1


def test_get_file_info_media_and_non_media(client, monkeypatch):
    monkeypatch.setattr(routes.config, 'DEFAULT_BASE_DIR', '/safe')
    monkeypatch.setattr(routes.os.path, 'abspath', lambda p: p)
    monkeypatch.setattr(routes.os.path, 'isabs', lambda p: True)
    monkeypatch.setattr(routes.os.path, 'exists', lambda p: True)
    monkeypatch.setattr(routes.os.path, 'isfile', lambda p: True)

    class Stat:
        st_size = 1
        st_mtime = 2

    monkeypatch.setattr(routes.os, 'stat', lambda p: Stat())

    monkeypatch.setattr(routes, 'get_media_duration', lambda p: 1.2)

    resp = client.get('/getFileInfo?path=/safe/a.mp3')
    assert resp.status_code == 200
    assert resp.json['code'] == 0
    assert resp.json['data']['isMediaFile'] is True
    assert resp.json['data']['duration'] == 1.2

    resp = client.get('/getFileInfo?path=/safe/a.txt')
    assert resp.status_code == 200
    assert resp.json['code'] == 0
    assert resp.json['data']['isMediaFile'] is False
    assert resp.json['data']['duration'] is None


def test_get_file_info_permission_and_exception(client, monkeypatch):
    monkeypatch.setattr(routes.config, 'DEFAULT_BASE_DIR', '/safe')
    monkeypatch.setattr(routes.os.path, 'abspath', lambda p: p)
    monkeypatch.setattr(routes.os.path, 'isabs', lambda p: True)
    monkeypatch.setattr(routes.os.path, 'exists', lambda p: True)
    monkeypatch.setattr(routes.os.path, 'isfile', lambda p: True)

    def raise_perm(_):
        raise PermissionError("no")

    monkeypatch.setattr(routes.os, 'stat', raise_perm)

    resp = client.get('/getFileInfo?path=/safe/a.mp3')
    assert resp.status_code == 200
    assert resp.json['code'] == -1
    assert 'Permission denied' in resp.json['msg']

    def raise_any(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(routes.os, 'stat', raise_any)
    resp = client.get('/getFileInfo?path=/safe/a.mp3')
    assert resp.status_code == 200
    assert resp.json['code'] == -1
    assert 'Error:' in resp.json['msg']
