"""
Agent 管理器
用于管理多个 DeviceAgent 实例
"""
import time
from typing import Dict
from core.device.agent import DeviceAgent
from core.config import app_logger
from core.services.playlist_mgr import playlist_mgr

log = app_logger

# 心跳超时时间（秒）
HEARTBEAT_TIMEOUT = 30

BUTTON_MAP = {
    "F13": ("B1", "play"),
    "F14": ("B1", "stop"),
    "F15": ("B2", "play"),
    "F16": ("B2", "stop"),
    "F17": ("B3", "play"),
    "F18": ("B3", "stop"),
}


class AgentMgr:
    """Agent 管理器，管理多个 DeviceAgent 实例"""

    def __init__(self):
        self._agents: Dict[str, DeviceAgent] = {}  # {agent_id: DeviceAgent}
        self._devices: Dict[str, dict] = {}  # {agent_id: {'heartbeat_time': timestamp, 'agent_id': str}}

    def _cleanup_expired_devices(self):
        """懒清理：清理过期设备"""
        current_time = time.time()
        expired_devices = []
        for agent_id, device_info in self._devices.items():
            heartbeat_time = device_info.get('heartbeat_time', 0)
            if current_time - heartbeat_time > HEARTBEAT_TIMEOUT:
                expired_devices.append(agent_id)

        for agent_id in expired_devices:
            self.remove_agent(agent_id)
            log.info(f"[AgentMgr] 移除过期设备: {agent_id}")

    def handle_heartbeat(self, client_ip: str, address: str, name: str = None, actions: list = None) -> dict:
        """
        处理设备心跳
        :param address: 设备地址（IP:PORT 格式）
        :param name: 设备名称
        :param actions: 设备支持的操作列表
        :return: 设备信息字典
        """
        current_time = time.time()
        # 先清理过期设备
        self._cleanup_expired_devices()

        agent_id = client_ip
        if agent_id not in self._devices:
            # 注册新设备
            self._agents[agent_id] = DeviceAgent(address=address, name=name)
            self._devices[agent_id] = {
                'heartbeat_time': current_time,
                'agent_id': agent_id,
                'register_time': current_time,
                'name': name or client_ip,
                'address': address,
                'actions': actions or []
            }
            log.info(f"[AgentMgr] 注册新设备: {address}, name={name}, actions={actions}")
        else:
            # 更新心跳时间和设备信息
            self._devices[agent_id]['heartbeat_time'] = current_time
            self._devices[agent_id]['name'] = name
            self._devices[agent_id]['actions'] = actions or []
            log.debug(f"[agent_id] 更新设备心跳: {agent_id}")

        return self._devices[agent_id]

    def get_agent(self, agent_id: str) -> DeviceAgent:
        """
        获取或创建 Agent 实例
        :param agent_id: Agent 标识，如果为 None 则返回默认 agent
        :return: DeviceAgent 实例
        """
        return self._agents[agent_id]

    def remove_agent(self, agent_id: str):
        """
        移除 Agent 实例
        :param agent_id: Agent 标识
        """
        self._devices.pop(agent_id, None)
        self._agents.pop(agent_id, None)

    def get_all_agents(self, action: str = None) -> Dict[str, dict]:
        """
        获取所有已注册的设备列表
        :return: 设备信息字典
        """
        # 先清理过期设备
        self._cleanup_expired_devices()
        if not action:
            return self._devices
        return [device for device in self._devices.values() if action in device['actions']]

    def handle_event(self, client_ip: str, key: str, value: str, action: str) -> tuple[int, str]:
        """
        处理事件
        :param client_ip: 客户端 IP
        :param key: 事件键
        :param value: 事件值
        :param type: 事件类型
        :return: 事件处理结果
        """
        _device = self._devices.get(client_ip)
        if not _device or action not in _device.get('actions', []):
            return -1, f"device not found {client_ip} or action not supported {action}"
        _agent = self.get_agent(client_ip)
        if not _agent:
            return -1, "agent not found"
        if action == "keyboard":
            button, action = BUTTON_MAP.get(key, (0, ""))
            playlist_mgr.trigger_button(button, action)
        return 0, "ok"


# 全局实例
agent_mgr = AgentMgr()
