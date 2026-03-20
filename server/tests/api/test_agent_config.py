"""测试 agent/config 接口。

用于验证设备配置更新功能。
"""
import pytest
from typing import Dict, Any


class TestAgentConfig:
    """测试 Agent 配置更新接口"""

    def test_update_agent_config_success(self, client):
        """测试成功更新设备配置"""
        # 先注册一个设备
        heartbeat_data = {'address': '192.168.1.100:8000', 'name': 'Test Device', 'actions': ['keyboard'], 'config': {}}
        response = client.post('/agent/heartbeat', json=heartbeat_data)
        assert response.status_code == 200

        # 更新配置
        config_data = {'agent_id': '192.168.1.100', 'config': {'volume': 80, 'shuffle': True, 'repeat_mode': 'loop'}}
        response = client.post('/agent/config', json=config_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('code') == 0

        # 验证配置已更新
        response = client.get('/agent/list')
        assert response.status_code == 200
        devices = response.get_json().get('data', [])
        assert len(devices) > 0
        device = next((d for d in devices if d['agent_id'] == '192.168.1.100'), None)
        assert device is not None
        assert device['config'].get('volume') == 80
        assert device['config'].get('shuffle') is True
        assert device['config'].get('repeat_mode') == 'loop'

    def test_update_agent_config_device_not_found(self, client):
        """测试更新不存在设备的配置"""
        config_data = {'agent_id': '192.168.1.200', 'config': {'volume': 50}}
        response = client.post('/agent/config', json=config_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('code') != 0
        assert 'device not found' in data.get('msg', '')

    def test_update_agent_config_invalid_body(self, client):
        """测试请求体格式错误"""
        # 缺少必需字段
        config_data = {'config': {'volume': 50}}
        response = client.post('/agent/config', json=config_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('code') != 0

    def test_update_agent_config_empty_config(self, client):
        """测试清空配置"""
        # 先注册一个设备
        heartbeat_data = {
            'address': '192.168.1.101:8000',
            'name': 'Test Device 2',
            'actions': ['keyboard'],
            'config': {
                'existing': 'value'
            }
        }
        response = client.post('/agent/heartbeat', json=heartbeat_data)
        assert response.status_code == 200

        # 清空配置
        config_data = {'agent_id': '192.168.1.101', 'config': {}}
        response = client.post('/agent/config', json=config_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('code') == 0

        # 验证配置已被清空
        response = client.get('/agent/list')
        assert response.status_code == 200
        devices = response.get_json().get('data', [])
        device = next((d for d in devices if d['agent_id'] == '192.168.1.101'), None)
        assert device is not None
        assert device['config'] == {}
