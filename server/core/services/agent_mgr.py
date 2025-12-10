"""
Agent 管理器
用于管理多个 DeviceAgent 实例
"""
import time
from typing import Optional, Dict
from core.device.agent import DeviceAgent
from core.log_config import root_logger

log = root_logger()

# 心跳超时时间（秒）
HEARTBEAT_TIMEOUT = 30


class AgentMgr:
    """Agent 管理器，管理多个 DeviceAgent 实例"""

    def __init__(self):
        self._agents: Dict[str, DeviceAgent] = {}  # {agent_id: DeviceAgent}
        self._default_agent: Optional[DeviceAgent] = None  # 默认 agent
        self._devices: Dict[str, dict] = {}  # {device_address: {'heartbeat_time': timestamp, 'agent_id': str}}

    def _cleanup_expired_devices(self):
        """懒清理：清理过期设备"""
        current_time = time.time()
        expired_devices = []
        for device_address, device_info in self._devices.items():
            heartbeat_time = device_info.get('heartbeat_time', 0)
            if current_time - heartbeat_time > HEARTBEAT_TIMEOUT:
                expired_devices.append(device_address)
        
        for device_address in expired_devices:
            device_info = self._devices.pop(device_address, None)
            if device_info:
                agent_id = device_info.get('agent_id')
                if agent_id and agent_id in self._agents:
                    del self._agents[agent_id]
                log.info(f"[AgentMgr] 移除过期设备: {device_address}")

    def handle_heartbeat(self, address: str, name: str = None, actions: list = None) -> dict:
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
            agent_id = f"agent_{address}"
            self._agents[agent_id] = DeviceAgent(address=address, name=name)
            self._devices[address] = {
                'heartbeat_time': current_time,
                'agent_id': agent_id,
                'register_time': current_time,
                'name': name,
                'address': address,
                'actions': actions or []
            }
            log.info(f"[AgentMgr] 注册新设备: {address}, name={name}")
        else:
            # 更新心跳时间和设备信息
            self._devices[address]['heartbeat_time'] = current_time
            if name is not None:
                self._devices[address]['name'] = name
                # 同时更新 DeviceAgent 实例的 name
                agent_id = self._devices[address].get('agent_id')
                if agent_id and agent_id in self._agents:
                    self._agents[agent_id].name = name
            if actions is not None:
                self._devices[address]['actions'] = actions
            log.debug(f"[AgentMgr] 更新设备心跳: {address}")
        
        return self._devices[address]

    def get_agent(self, agent_id: str = None, address: str = None) -> DeviceAgent:
        """
        获取或创建 Agent 实例
        :param agent_id: Agent 标识，如果为 None 则返回默认 agent
        :param address: Agent 服务地址（IP:PORT 格式），如果提供则创建新实例
        :return: DeviceAgent 实例
        """
        # 如果没有指定 agent_id，返回默认 agent
        if agent_id is None:
            if self._default_agent is None:
                self._default_agent = DeviceAgent(address=address)
            return self._default_agent

        # 如果指定了 agent_id，从缓存中获取或创建
        if agent_id not in self._agents:
            self._agents[agent_id] = DeviceAgent(address=address)
            log.debug(f"[AgentMgr] 创建新的 Agent 实例: {agent_id}")
        return self._agents[agent_id]

    def remove_agent(self, agent_id: str):
        """
        移除 Agent 实例
        :param agent_id: Agent 标识
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            log.debug(f"[AgentMgr] 移除 Agent 实例: {agent_id}")

    def get_all_agents(self) -> Dict[str, DeviceAgent]:
        """
        获取所有 Agent 实例
        :return: Agent 字典
        """
        return self._agents.copy()

    def get_all_devices(self) -> Dict[str, dict]:
        """
        获取所有已注册的设备列表
        :return: 设备信息字典
        """
        # 先清理过期设备
        self._cleanup_expired_devices()
        return self._devices


# 全局实例
agent_mgr = AgentMgr()
