"""
Agent 管理器
用于管理多个 DeviceAgent 实例
"""
import time
from typing import Dict
from core.device.agent import DeviceAgent
from core.log_config import root_logger

log = root_logger()

# 心跳超时时间（秒）
HEARTBEAT_TIMEOUT = 30


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

        if address not in self._devices:
            # 注册新设备
            agent_id = client_ip
            self._agents[agent_id] = DeviceAgent(address=address, name=name)
            self._devices[address] = {
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
            self._devices[address]['heartbeat_time'] = current_time
            self._devices[address]['name'] = name
            self._devices[address]['actions'] = actions or []
            log.debug(f"[AgentMgr] 更新设备心跳: {address}")

        return self._devices[address]

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


# 全局实例
agent_mgr = AgentMgr()
