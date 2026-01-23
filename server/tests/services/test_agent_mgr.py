import pytest
import time
from unittest.mock import patch, MagicMock

from core.device.agent import DeviceAgent
from core.services.agent_mgr import AgentMgr, HEARTBEAT_TIMEOUT


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
    address = '192.168.1.100:8080'
    name = 'Test Device'
    actions = ['play', 'stop']

    device_info = agent_mgr.handle_heartbeat(client_ip, address, name, actions)

    assert client_ip in agent_mgr._devices
    assert client_ip in agent_mgr._agents
    assert device_info['agent_id'] == client_ip
    assert device_info['name'] == name
    assert device_info['actions'] == actions
    assert 'register_time' in device_info


def test_handle_heartbeat_existing_device(agent_mgr):
    """Test that an existing device's heartbeat and info are updated."""
    client_ip = '192.168.1.101'
    address = '192.168.1.101:8080'

    # First heartbeat
    agent_mgr.handle_heartbeat(client_ip, address, 'Old Name', ['play'])
    first_heartbeat_time = agent_mgr._devices[client_ip]['heartbeat_time']

    time.sleep(0.1)  # Ensure time progresses

    # Second heartbeat with updated info
    updated_name = 'New Name'
    updated_actions = ['play', 'pause']
    agent_mgr.handle_heartbeat(client_ip, address, updated_name, updated_actions)

    assert agent_mgr._devices[client_ip]['name'] == updated_name
    assert agent_mgr._devices[client_ip]['actions'] == updated_actions
    assert agent_mgr._devices[client_ip]['heartbeat_time'] > first_heartbeat_time


@patch('core.services.agent_mgr.time.time')
def test_cleanup_expired_devices(mock_time, agent_mgr):
    """Test that expired devices are removed after cleanup."""
    client_ip_active = '192.168.1.102'
    client_ip_expired = '192.168.1.103'

    # Register an active device
    mock_time.return_value = 1000
    agent_mgr.handle_heartbeat(client_ip_active, f'{client_ip_active}:8080')

    # Register an expired device (as if it was registered in the past)
    mock_time.return_value = 1000 - HEARTBEAT_TIMEOUT - 1
    agent_mgr.handle_heartbeat(client_ip_expired, f'{client_ip_expired}:8080')

    # Set current time to now
    mock_time.return_value = 1000

    # Trigger cleanup
    agent_mgr._cleanup_expired_devices()

    assert client_ip_active in agent_mgr._devices
    assert client_ip_expired not in agent_mgr._devices
    assert client_ip_expired not in agent_mgr._agents


def test_get_all_agents(agent_mgr):
    """Test getting all registered agents and filtering by action."""
    agent_mgr.handle_heartbeat('1.1.1.1', '1.1.1.1:80', 'Device A', ['play', 'stop'])
    agent_mgr.handle_heartbeat('2.2.2.2', '2.2.2.2:80', 'Device B', ['pause', 'stop'])

    all_agents = agent_mgr.get_all_agents()
    assert len(all_agents) == 2
    assert '1.1.1.1' in all_agents

    stop_agents = agent_mgr.get_all_agents(action='stop')
    assert len(stop_agents) == 2

    play_agents = agent_mgr.get_all_agents(action='play')
    assert len(play_agents) == 1
    assert play_agents[0]['agent_id'] == '1.1.1.1'


@patch('core.services.agent_mgr.playlist_mgr')
def test_handle_event_keyboard(mock_playlist_mgr, agent_mgr):
    """Test that keyboard events are correctly mapped and handled."""
    client_ip = '3.3.3.3'
    agent_mgr.handle_heartbeat(client_ip, f'{client_ip}:80', 'Keyboard-Device', ['keyboard'])

    # Test a mapped key
    code, msg = agent_mgr.handle_event(client_ip, 'F13', 'pressed', 'keyboard')
    assert code == 0
    assert msg == 'ok'
    mock_playlist_mgr.trigger_button.assert_called_once_with('B1', 'play')

    # Test an unmapped key
    mock_playlist_mgr.reset_mock()
    code, msg = agent_mgr.handle_event(client_ip, 'UNKNOWN_KEY', 'pressed', 'keyboard')
    assert code == 0  # The function returns ok even for unmapped keys
    mock_playlist_mgr.trigger_button.assert_called_once_with(0, '')


def test_handle_event_unsupported_action(agent_mgr):
    """Test that events for unsupported actions are rejected."""
    client_ip = '4.4.4.4'
    agent_mgr.handle_heartbeat(client_ip, f'{client_ip}:80', 'Simple-Device', ['play'])

    code, msg = agent_mgr.handle_event(client_ip, 'F13', 'pressed', 'keyboard')
    assert code == -1
    assert 'action not supported' in msg


def test_get_agent(agent_mgr):
    """Test retrieving a specific agent."""
    client_ip = '5.5.5.5'
    agent_mgr.handle_heartbeat(client_ip, f'{client_ip}:80')

    agent = agent_mgr.get_agent(client_ip)
    assert agent is not None
    assert agent.base_url == f'http://{client_ip}:80'

    with pytest.raises(KeyError):
        agent_mgr.get_agent('non-existent-ip')
