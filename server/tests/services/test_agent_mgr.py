import pytest
import time
from unittest.mock import patch, MagicMock

from core.device.agent import DeviceAgent
from core.services.agent_mgr import AgentMgr, HEARTBEAT_TIMEOUT
from core.api.types import AgentHeartbeatData


class MockDeviceAgent(DeviceAgent):
    """A concrete implementation of DeviceAgent for testing purposes."""

    def play(self, source: str, **kwargs):
        return {"code": 0, "msg": "played"}

    def stop(self):
        return {"code": 0, "msg": "stopped"}

    def get_status(self):
        return {"state": "stopped"}

    def get_volume(self) -> int | None:
        return 50

    def set_volume(self, volume: int) -> bool:
        return True


@pytest.fixture
def agent_mgr():
    """Provides a clean AgentMgr instance for each test."""
    with patch('core.services.agent_mgr.DeviceAgent', new=MockDeviceAgent):
        mgr = AgentMgr()
        yield mgr


def test_handle_heartbeat_new_device(agent_mgr):
    """Test that a new device is registered correctly on first heartbeat."""
    client_ip = '192.168.1.100'
    data = AgentHeartbeatData(
        address='192.168.1.100:8080',
        name='Test Device',
        actions=['play', 'stop']
    )

    device_info = agent_mgr.handle_heartbeat(client_ip, data)

    assert client_ip in agent_mgr._devices
    assert client_ip in agent_mgr._agents
    assert device_info['agent_id'] == client_ip
    assert device_info['name'] == 'Test Device'
    assert device_info['actions'] == ['play', 'stop']
    assert 'register_time' in device_info


def test_handle_heartbeat_existing_device(agent_mgr):
    """Test that an existing device's heartbeat and info are updated."""
    client_ip = '192.168.1.101'

    # First heartbeat
    agent_mgr.handle_heartbeat(client_ip, AgentHeartbeatData(
        address='192.168.1.101:8080',
        name='Old Name',
        actions=['play']
    ))
    first_heartbeat_time = agent_mgr._devices[client_ip]['heartbeat_time']

    time.sleep(0.1)

    # Second heartbeat with updated info
    agent_mgr.handle_heartbeat(client_ip, AgentHeartbeatData(
        address='192.168.1.101:8080',
        name='New Name',
        actions=['play', 'pause']
    ))

    assert agent_mgr._devices[client_ip]['name'] == 'New Name'
    assert agent_mgr._devices[client_ip]['actions'] == ['play', 'pause']
    assert agent_mgr._devices[client_ip]['heartbeat_time'] > first_heartbeat_time


@patch('core.services.agent_mgr.time.time')
def test_cleanup_expired_devices(mock_time, agent_mgr):
    """Test that expired devices are removed after cleanup."""
    client_ip_active = '192.168.1.102'
    client_ip_expired = '192.168.1.103'

    mock_time.return_value = 1000
    agent_mgr.handle_heartbeat(client_ip_active, AgentHeartbeatData(
        address=f'{client_ip_active}:8080'
    ))

    mock_time.return_value = 1000 - HEARTBEAT_TIMEOUT - 1
    agent_mgr.handle_heartbeat(client_ip_expired, AgentHeartbeatData(
        address=f'{client_ip_expired}:8080'
    ))

    mock_time.return_value = 1000

    agent_mgr._cleanup_expired_devices()

    assert client_ip_active in agent_mgr._devices
    assert client_ip_expired not in agent_mgr._devices
    assert client_ip_expired not in agent_mgr._agents


def test_get_all_agents(agent_mgr):
    """Test getting all registered agents and filtering by action."""
    agent_mgr.handle_heartbeat('1.1.1.1', AgentHeartbeatData(
        address='1.1.1.1:80', name='Device A', actions=['play', 'stop']
    ))
    agent_mgr.handle_heartbeat('2.2.2.2', AgentHeartbeatData(
        address='2.2.2.2:80', name='Device B', actions=['pause', 'stop']
    ))

    all_agents = agent_mgr.get_all_agents()
    assert len(all_agents) == 2
    assert '1.1.1.1' in all_agents

    stop_agents = agent_mgr.get_all_agents(action='stop')
    assert len(stop_agents) == 2

    play_agents = agent_mgr.get_all_agents(action='play')
    assert len(play_agents) == 1
    assert play_agents['1.1.1.1']['agent_id'] == '1.1.1.1'


@patch('core.services.agent_mgr.playlist_mgr')
def test_handle_event_keyboard(mock_playlist_mgr, agent_mgr):
    """Test that keyboard events are correctly mapped and handled."""
    client_ip = '3.3.3.3'
    agent_mgr.handle_heartbeat(client_ip, AgentHeartbeatData(
        address=f'{client_ip}:80', name='Keyboard-Device', actions=['keyboard']
    ))

    code, msg = agent_mgr.handle_event(client_ip, 'F13', 'pressed', 'keyboard')
    assert code == 0
    assert msg == 'ok'
    mock_playlist_mgr.trigger_button.assert_called_once_with('B1', 'play')

    mock_playlist_mgr.reset_mock()
    code, msg = agent_mgr.handle_event(client_ip, 'UNKNOWN_KEY', 'pressed', 'keyboard')
    assert code == 0
    mock_playlist_mgr.trigger_button.assert_called_once_with('0', '')


def test_handle_event_unsupported_action(agent_mgr):
    """Test that events for unsupported actions are rejected."""
    client_ip = '4.4.4.4'
    agent_mgr.handle_heartbeat(client_ip, AgentHeartbeatData(
        address=f'{client_ip}:80', name='Simple-Device', actions=['play']
    ))

    code, msg = agent_mgr.handle_event(client_ip, 'F13', 'pressed', 'keyboard')
    assert code == -1
    assert 'action not supported' in msg


def test_get_agent(agent_mgr):
    """Test retrieving a specific agent."""
    client_ip = '5.5.5.5'
    agent_mgr.handle_heartbeat(client_ip, AgentHeartbeatData(
        address=f'{client_ip}:80'
    ))

    agent = agent_mgr.get_agent(client_ip)
    assert agent is not None
    assert agent.base_url == f'http://{client_ip}:80'

    with pytest.raises(KeyError):
        agent_mgr.get_agent('non-existent-ip')
