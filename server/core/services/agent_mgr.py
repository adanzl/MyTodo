"""
Agent 管理器
用于管理多个 DeviceAgent 实例
"""
import time
from typing import Dict, Optional, List, Any, Union
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

    def __init__(self) -> None:
        self._agents: Dict[str, DeviceAgent] = {}  # {agent_id: DeviceAgent}
        self._devices: Dict[str, Dict[str, Any]] = {}  # {agent_id: {'heartbeat_time': timestamp, 'agent_id': str}}

    def _cleanup_expired_devices(self) -> None:
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

    def handle_heartbeat(self,
                         client_ip: str,
                         address: str,
                         name: Optional[str] = None,
                         actions: Optional[List[str]] = None) -> Dict[str, Any]:
        """处理并注册设备的周期性心跳。

        如果设备是首次上报，则为其创建并注册一个新的 Agent 实例；
        否则，更新其心跳时间及设备信息。

        Args:
            client_ip (str): 上报心跳的客户端 IP，作为 Agent 的唯一标识。
            address (str): 设备的访问地址，通常是 IP:PORT 格式。
            name (Optional[str]): 设备名称。
            actions (Optional[List[str]]): 设备支持的操作列表。

        Returns:
            Dict[str, Any]: 更新或创建后的设备信息字典。
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
        """获取指定 ID 的 Agent 实例。

        Args:
            agent_id (str): Agent 唯一标识。

        Returns:
            DeviceAgent: 对应的 Agent 实例。

        Raises:
            KeyError: 当 `agent_id` 未注册时抛出。
        """
        return self._agents[agent_id]

    def remove_agent(self, agent_id: str) -> None:
        """移除指定 ID 的 Agent 实例及其设备信息。

        Args:
            agent_id (str): 要移除的 Agent 的唯一标识。
        """
        self._devices.pop(agent_id, None)
        self._agents.pop(agent_id, None)

    def get_all_agents(self, action: Optional[str] = None) -> Union[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
        """
        获取所有已注册的设备列表
        :param action: 可选的操作类型，如果提供则只返回支持该操作的设备列表
        :return: 设备信息字典或设备列表
        """
        # 先清理过期设备
        self._cleanup_expired_devices()
        if not action:
            return self._devices
        return [device for device in self._devices.values() if action in device.get('actions', [])]

    def handle_event(self, client_ip: str, key: str, value: str, action: str) -> tuple[int, str]:
        _ = value
        """处理来自 Agent 的事件上报。

        目前主要用于处理键盘事件，并将特定按键映射为播放控制操作。

        Args:
            client_ip (str): 客户端 IP（Agent 唯一标识）。
            key (str): 事件键（例如键盘按键）。
            value (str): 事件值（预留字段，当前未使用）。
            action (str): 事件动作类型（例如 "keyboard"）。

        Returns:
            tuple[int, str]: (code, msg)。code=0 表示成功。
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
