"""测试 agent/config 接口。

用于验证设备配置更新功能。
"""
import pytest
from unittest.mock import MagicMock
from flask import Flask

import core.api.agent_routes as agent_routes


@pytest.fixture
def app(monkeypatch):
    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(agent_routes.agent_bp)

    def _read_json_from_request():
        return (agent_routes.request.get_json(silent=True) or {})

    monkeypatch.setattr(agent_routes, "read_json_from_request", _read_json_from_request)

    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestAgentConfig:
    """测试 Agent 配置更新接口"""

    def test_update_agent_config_success(self, client, monkeypatch):
        """测试成功更新设备配置"""
        monkeypatch.setattr(agent_routes.agent_mgr, "update_agent_config",
                            lambda data: (0, "ok"))
        monkeypatch.setattr(agent_routes.agent_mgr, "get_all_agents", lambda: {
            "192.168.1.100": {
                "address": "192.168.1.100:8000",
                "name": "Test Device",
                "agent_id": "192.168.1.100",
                "actions": ["keyboard"],
                "heartbeat_time": 1000,
                "register_time": 1,
                "config": {"volume": 80, "shuffle": True, "repeat_mode": "loop"},
                "keyboard": {},
            }
        })

        config_data = {'agent_id': '192.168.1.100', 'type': 'update', 'config': {'volume': 80, 'shuffle': True, 'repeat_mode': 'loop'}}
        response = client.post('/agent/config', json=config_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('code') == 0

        response = client.get('/agent/list')
        assert response.status_code == 200
        devices = response.get_json().get('data', [])
        assert len(devices) > 0
        device = next((d for d in devices if d['agent_id'] == '192.168.1.100'), None)
        assert device is not None
        assert device['config'].get('volume') == 80
        assert device['config'].get('shuffle') is True
        assert device['config'].get('repeat_mode') == 'loop'

    def test_update_agent_config_device_not_found(self, client, monkeypatch):
        """测试更新不存在设备的配置"""
        monkeypatch.setattr(agent_routes.agent_mgr, "update_agent_config",
                            lambda data: (-1, "device not found: 192.168.1.200"))

        config_data = {'agent_id': '192.168.1.200', 'type': 'update', 'config': {'volume': 50}}
        response = client.post('/agent/config', json=config_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('code') != 0
        assert 'device not found' in data.get('msg', '')

    def test_update_agent_config_invalid_body(self, client):
        """测试请求体格式错误"""
        config_data = {'config': {'volume': 50}}
        response = client.post('/agent/config', json=config_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('code') != 0

    def test_update_agent_config_empty_config(self, client, monkeypatch):
        """测试清空配置"""
        monkeypatch.setattr(agent_routes.agent_mgr, "update_agent_config",
                            lambda data: (0, "ok"))
        monkeypatch.setattr(agent_routes.agent_mgr, "get_all_agents", lambda: {
            "192.168.1.101": {
                "address": "192.168.1.101:8000",
                "name": "Test Device 2",
                "agent_id": "192.168.1.101",
                "actions": ["keyboard"],
                "heartbeat_time": 1000,
                "register_time": 1,
                "config": {},
                "keyboard": {},
            }
        })

        config_data = {'agent_id': '192.168.1.101', 'type': 'update', 'config': {}}
        response = client.post('/agent/config', json=config_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('code') == 0

        response = client.get('/agent/list')
        assert response.status_code == 200
        devices = response.get_json().get('data', [])
        device = next((d for d in devices if d['agent_id'] == '192.168.1.101'), None)
        assert device is not None
        assert device['config'] == {}
