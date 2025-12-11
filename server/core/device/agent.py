"""
Device Agent HTTP 客户端
用于通过内网调用 device_agent 服务的接口
"""
import os
import requests
from typing import Optional, Dict, Any
from core.log_config import root_logger

log = root_logger()

# 完整的服务URL
DEVICE_AGENT_BASE_URL = f"http://192.168.50.184:8000"

# 请求超时时间（秒）
DEVICE_AGENT_TIMEOUT = 30


class DeviceAgent:
    """Device Agent HTTP 客户端"""

    def __init__(self, address: str = None, name: str = None):
        """
        初始化客户端
        :param address: Agent 服务地址（IP:PORT 格式，如 "192.168.50.184:8000"），如果为 None 则使用默认配置
        :param name: 设备名称
        """
        base_url = address or DEVICE_AGENT_BASE_URL
        # 确保 base_url 有 http:// 前缀
        if base_url and not base_url.startswith(('http://', 'https://')):
            base_url = f"http://{base_url}"
        self.base_url = base_url
        self.timeout = DEVICE_AGENT_TIMEOUT
        self.name = name

    def _request(self,
                 method: str,
                 endpoint: str,
                 params: Optional[Dict] = None,
                 json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        发送HTTP请求
        :param method: HTTP方法 (GET, POST等)
        :param endpoint: API端点路径（如 /bluetooth/scan）
        :param params: URL参数（用于GET请求）
        :param json_data: JSON请求体（用于POST请求）
        :return: 响应数据字典
        """
        url = f"{self.base_url}{endpoint}"

        try:
            log.debug(f"[DeviceAgent] {method} {url}, params={params}, json={json_data}")

            response = requests.request(method=method, url=url, params=params, json=json_data, timeout=self.timeout)

            # 检查HTTP状态码
            response.raise_for_status()

            # 解析JSON响应
            result = response.json()
            log.debug(f"[DeviceAgent] Response: {result}")
            return result

        except requests.exceptions.Timeout:
            log.error(f"[DeviceAgent] Request timeout: {url}")
            return {"code": -1, "msg": "请求超时"}
        except requests.exceptions.ConnectionError as e:
            log.error(f"[DeviceAgent] Connection error: {url}, error: {e}")
            return {"code": -1, "msg": f"连接失败: {str(e)}"}
        except requests.exceptions.HTTPError as e:
            log.error(f"[DeviceAgent] HTTP error: {url}, status: {response.status_code}, error: {e}")
            return {"code": -1, "msg": f"HTTP错误: {response.status_code}"}
        except Exception as e:
            log.error(f"[DeviceAgent] Request error: {url}, error: {e}")
            return {"code": -1, "msg": f"请求失败: {str(e)}"}

    # ========== 蓝牙相关接口 ==========

    def bluetooth_scan(self, timeout: float = 5.0) -> Dict[str, Any]:
        """
        扫描蓝牙设备
        :param timeout: 扫描超时时间（秒）
        :return: 设备列表
        """
        return self._request("GET", "/bluetooth/scan", params={"timeout": timeout})

    def bluetooth_get_devices(self) -> Dict[str, Any]:
        """
        获取设备列表
        :return: 设备列表
        """
        return self._request("GET", "/bluetooth/devices")

    def bluetooth_get_device(self, address: str) -> Dict[str, Any]:
        """
        获取设备信息
        :param address: 设备地址
        :return: 设备信息
        """
        return self._request("GET", "/bluetooth/device", params={"address": address})

    def bluetooth_connect(self, address: str) -> Dict[str, Any]:
        """
        连接蓝牙设备
        :param address: 设备地址
        :return: 连接结果
        """
        return self._request("POST", "/bluetooth/connect", json_data={"address": address})

    def bluetooth_disconnect(self, address: str) -> Dict[str, Any]:
        """
        断开蓝牙设备
        :param address: 设备地址
        :return: 断开结果
        """
        return self._request("POST", "/bluetooth/disconnect", json_data={"address": address})

    def bluetooth_get_connected(self) -> Dict[str, Any]:
        """
        获取已连接的蓝牙设备列表
        :return: 已连接设备列表
        """
        return self._request("GET", "/bluetooth/connected")

    def bluetooth_get_paired(self) -> Dict[str, Any]:
        """
        获取已配对的蓝牙设备列表
        :return: 已配对设备列表
        """
        return self._request("GET", "/bluetooth/paired")


    # ========== 统一 Device 接口 ==========
    def play(self, url: str) -> tuple[int, str]:
        """
        播放媒体文件【OUT】
        :param url: 媒体文件路径或URL
        :return: (错误码, 消息)
        """
        # DeviceAgent 需要设备地址，从初始化时的 base_url 中提取 或者使用默认的蓝牙设备地址
        data = {"file_path": url}
        result = self._request("POST", "/media/play", json_data=data)
        code = result.get("code", -1)
        msg = result.get("msg", "未知错误")
        return (code, msg)

    def stop(self) -> tuple[int, str]:
        """
        停止播放【OUT】
        :return: (错误码, 消息)
        """
        result = self._request("POST", "/media/stop")
        code = result.get("code", -1)
        msg = result.get("msg", "未知错误")
        return (code, msg)

    def get_status(self) -> tuple[int, dict]:
        """
        获取播放状态信息（合并 transport_info 和 position_info）【OUT】
        :return: (错误码, 状态字典) 格式: {'state', 'status', 'track', 'duration', 'position'}
        """
        try:
            # 尝试调用状态接口（如果存在）
            result = self._request("GET", "/media/status")
            if result.get("code") == 0:
                data = result.get("data", {})
                return (0, data)
        except Exception:
            pass

        # 如果接口不存在，返回未知状态
        return (-1, {"error": "设备不支持获取传输状态"})

    # ========== Agent 接口 ==========
    
    def mock(self, action: str, key: str = None, value: str = None) -> Dict[str, Any]:
        """
        Mock接口，用于模拟设备操作
        :param action: 操作类型，如 "keyboard"
        :param key: 键值
        :param value: 值
        :return: 响应结果
        """
        if action == "keyboard":
            # 向 agent 的 /keyboard/test 发送 key 和 value
            json_data = {}
            if key is not None:
                json_data["key"] = key
            if value is not None:
                json_data["value"] = value
            return self._request("POST", "/keyboard/test", json_data=json_data)
        else:
            return {"code": -1, "msg": f"不支持的 action: {action}"}