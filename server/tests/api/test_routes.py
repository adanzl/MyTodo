import json
import os
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

# Since routes.py imports from core, we need to add the project root to the path
import core.api.routes as routes


@pytest.fixture
def app(monkeypatch):
    """Create a Flask app instance for testing."""
    # Mock managers before app creation to prevent real connections
    monkeypatch.setattr(routes, 'db_mgr', MagicMock())
    monkeypatch.setattr(routes, 'rds_mgr', MagicMock())
    monkeypatch.setattr(routes, 'AILocal', MagicMock())

    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(routes.api_bp)

    def _read_json_from_request():
        return routes.request.get_json(silent=True) or {}

    monkeypatch.setattr(routes, "read_json_from_request", _read_json_from_request)

    yield app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


# --- Test DB/Save Endpoints ---


def test_get_save_ok(client, monkeypatch):
    mock_db_mgr = MagicMock()
    mock_db_mgr.get_save.return_value = {"code": 0, "data": {"id": 1, "content": "test"}}
    monkeypatch.setattr(routes, 'db_mgr', mock_db_mgr)

    response = client.get('/getSave?id=1')
    assert response.status_code == 200
    data = response.get_json()
    assert data["code"] == 0
    assert data["data"]["content"] == "test"
    mock_db_mgr.get_save.assert_called_once_with(1)


def test_get_save_invalid_id(client):
    response = client.get('/getSave?id=abc')
    assert response.status_code == 200
    data = response.get_json()
    assert data["code"] == -1
    assert "must be int" in data["msg"]


def test_set_save_ok(client, monkeypatch):
    mock_db_mgr = MagicMock()
    mock_db_mgr.set_save.return_value = {"code": 0}
    monkeypatch.setattr(routes, 'db_mgr', mock_db_mgr)

    payload = {"id": 1, "user": "testuser", "data": {"key": "value"}}
    response = client.post('/setSave', data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 200
    assert response.get_json()["code"] == 0
    mock_db_mgr.set_save.assert_called_once_with(1, "testuser", '{"key": "value"}')


# --- Test Redis Endpoints ---


def test_get_rds_data_ok(client, monkeypatch):
    mock_rds_mgr = MagicMock()
    mock_rds_mgr.get_str.return_value = "my-redis-value"
    monkeypatch.setattr(routes, 'rds_mgr', mock_rds_mgr)

    response = client.get('/getRdsData?table=t&id=1')
    assert response.status_code == 200
    data = response.get_json()
    assert data["code"] == 0
    assert data["data"] == "my-redis-value"
    mock_rds_mgr.get_str.assert_called_once_with("t:1")


def test_set_rds_data_ok(client, monkeypatch):
    mock_rds_mgr = MagicMock()
    monkeypatch.setattr(routes, 'rds_mgr', mock_rds_mgr)

    payload = {"table": "t", "data": {"id": "1", "value": "v"}}
    response = client.post('/setRdsData', data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 200
    data = response.get_json()
    assert data["code"] == 0
    assert data["data"] == "1"
    mock_rds_mgr.set.assert_called_once_with("t:1", "v")


def test_add_rds_list_ok(client, monkeypatch):
    mock_rds_mgr = MagicMock()
    monkeypatch.setattr(routes, 'rds_mgr', mock_rds_mgr)

    payload = {"key": "my-list", "value": "item1"}
    response = client.post('/addRdsList', data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 200
    data = response.get_json()
    assert data["code"] == 0
    assert data["data"] == "item1"
    mock_rds_mgr.rpush.assert_called_once_with("my-list", "item1")


def test_add_rds_list_missing_params(client):
    response = client.post('/addRdsList', data=json.dumps({"key": "my-list"}), content_type='application/json')
    assert response.status_code == 200
    assert response.get_json()["code"] == -1
    assert "key and value are required" in response.get_json()["msg"]


# --- Test File System Endpoints (Security) ---


def test_list_directory_path_traversal(client):
    response = client.get('/listDirectory?path=../..')
    assert response.status_code == 200
    data = response.get_json()
    assert data["code"] == -1
    assert "Path traversal not allowed" in data["msg"]


@patch('core.api.routes.os.path.exists', return_value=True)
@patch('core.api.routes.os.path.isdir', return_value=True)
@patch('core.api.routes.os.access', return_value=True)
@patch('core.api.routes.os.listdir', return_value=['file1.mp3', 'dir1'])
@patch('core.api.routes.os.stat')
def test_list_directory_ok(mock_stat, mock_listdir, mock_access, mock_isdir, mock_exists, client):
    # Mock stat to return basic file info
    mock_stat.return_value.st_size = 1024
    mock_stat.return_value.st_mtime = 1234567890

    # Mock isdir for the entries
    def isdir_side_effect(path):
        if path.endswith('dir1'):
            return True
        return False

    mock_isdir.side_effect = isdir_side_effect

    response = client.get('/listDirectory?path=/mnt/music')
    assert response.status_code == 200
    data = response.get_json()

    assert data["code"] == 0
    assert data["currentPath"] == '/mnt/music'
    assert len(data["data"]) == 2
    # Directories should come first due to sorting
    assert data["data"][0]["name"] == 'dir1'
    assert data["data"][0]["isDirectory"] is True
    assert data["data"][1]["name"] == 'file1.mp3'
    assert data["data"][1]["isDirectory"] is False


def test_get_file_info_path_traversal(client):
    response = client.get('/getFileInfo?path=~/some/path')
    assert response.status_code == 200
    data = response.get_json()
    assert data["code"] == -1
    assert "Path traversal not allowed" in data["msg"]


# --- Test Lottery Endpoint ---


@pytest.fixture
def mock_lottery_deps(monkeypatch):
    mock_db = MagicMock()
    mock_rds = MagicMock()

    # Mock user score
    mock_db.get_data.return_value = {"code": 0, "data": {"id": 1, "score": 100}}
    # Mock gift pool
    mock_db.get_list.return_value = {
        "code": 0,
        "data": {
            "data": [{
                "id": 101,
                "name": "Gift A"
            }, {
                "id": 102,
                "name": "Gift B"
            }]
        }
    }
    # Mock category cost
    mock_db.get_data.side_effect = [
        {
            "code": 0,
            "data": {
                "id": 1,
                "score": 100
            }
        },  # First call for user score
        {
            "code": 0,
            "data": {
                "id": 2,
                "name": "cat",
                "cost": 10
            }
        }  # Second call for category
    ]
    mock_db.add_score.return_value = {"code": 0}

    monkeypatch.setattr(routes, 'db_mgr', mock_db)
    monkeypatch.setattr(routes, 'rds_mgr', mock_rds)
    monkeypatch.setattr(routes.random, 'choice', lambda x: x[0])  # Make choice deterministic

    return mock_db, mock_rds


def test_do_lottery_ok(client, mock_lottery_deps):
    mock_db, _ = mock_lottery_deps

    payload = {"user_id": "1", "cate_id": "2"}
    response = client.post('/doLottery', data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 200
    data = response.get_json()
    assert data["code"] == 0
    assert data["msg"] == "抽奖成功"
    assert data["data"]["gift"]["id"] == 101
    assert data["data"]["fee"] == 10
    # Verify score was deducted
    mock_db.add_score.assert_called_once_with(1, -10, 'lottery', '获得[101]Gift A')


def test_do_lottery_not_enough_score(client, mock_lottery_deps):
    mock_db, _ = mock_lottery_deps
    # Override user score to be insufficient
    mock_db.get_data.side_effect = [{
        "code": 0,
        "data": {
            "id": 1,
            "score": 5
        }
    }, {
        "code": 0,
        "data": {
            "id": 2,
            "name": "cat",
            "cost": 10
        }
    }]

    payload = {"user_id": "1", "cate_id": "2"}
    response = client.post('/doLottery', data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 200
    data = response.get_json()
    assert data["code"] == -1
    assert data["msg"] == "Not enough score"
