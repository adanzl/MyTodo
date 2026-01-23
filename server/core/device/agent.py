"""
Device Agent HTTP 客户端
用于通过内网调用 device_agent 服务的接口
"""
import requests
from typing import Optional, Dict, Any
from core.config import app_logger
from core.device.base import DeviceBase

log = app_logger

# 完整的服务URL
DEVICE_AGENT_BASE_URL = f"http://192.168.50.184:8000"

# 请求超时时间（秒）
DEVICE_AGENT_TIMEOUT = 30


class DeviceAgent(DeviceBase):
    """Device Agent HTTP 客户端"""

    def __init__(self, address: Optional[str] = None, name: Optional[str] = None) -> None:
        """初始化客户端。

        Args:
            address (Optional[str]): Agent 服务地址（IP:PORT 格式），如果为 None 则使用默认配置。
            name (Optional[str]): 设备名称。
        """
        super().__init__(name=name)
        base_url = address or DEVICE_AGENT_BASE_URL
        # 确保 base_url 有 http:// 前缀
        if base_url and not base_url.startswith(('http://', 'https://')):
            base_url = f"http://{base_url}"
        self.base_url = base_url
        self.timeout = DEVICE_AGENT_TIMEOUT

    def _request(self,
                 method: str,
                 endpoint: str,
                 params: Optional[Dict[str, Any]] = None,
                 json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """向 Agent 服务发送 HTTP 请求的内部封装。

        Args:
            method (str): HTTP 方法 (如 "GET", "POST")。
            endpoint (str): API 端点路径 (如 "/bluetooth/scan")。
            params (Optional[Dict[str, Any]]): URL 查询参数。
            json_data (Optional[Dict[str, Any]]): JSON 请求体。

        Returns:
            Dict[str, Any]: 从 Agent 服务返回的 JSON 响应。错误时返回包含 code 和 msg 的字典。
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
        """请求 Agent 扫描蓝牙设备。

        Args:
            timeout (float): 扫描超时时间（秒）。

        Returns:
            Dict[str, Any]: Agent 返回的响应字典。
        """
        return self._request("GET", "/bluetooth/scan", params={"timeout": timeout})

    def bluetooth_get_devices(self) -> Dict[str, Any]:
        """请求 Agent 获取已发现的蓝牙设备列表。

        Returns:
            Dict[str, Any]: Agent 返回的响应字典。
        """
        return self._request("GET", "/bluetooth/devices")

    def bluetooth_get_device(self, address: str) -> Dict[str, Any]:
        """请求 Agent 获取指定蓝牙设备的信息。

        Args:
            address (str): 设备的蓝牙地址。

        Returns:
            Dict[str, Any]: Agent 返回的响应字典。
        """
        return self._request("GET", "/bluetooth/device", params={"address": address})

    def bluetooth_connect(self, address: str) -> Dict[str, Any]:
        """请求 Agent 连接指定的蓝牙设备。

        Args:
            address (str): 设备的蓝牙地址。

        Returns:
            Dict[str, Any]: Agent 返回的响应字典。
        """
        return self._request("POST", "/bluetooth/connect", json_data={"address": address})

    def bluetooth_disconnect(self, address: str) -> Dict[str, Any]:
        """请求 Agent 断开指定蓝牙设备的连接。

        Args:
            address (str): 设备的蓝牙地址。

        Returns:
            Dict[str, Any]: Agent 返回的响应字典。
        """
        return self._request("POST", "/bluetooth/disconnect", json_data={"address": address})

    def bluetooth_get_connected(self) -> Dict[str, Any]:
        """请求 Agent 获取已连接的蓝牙设备列表。

        Returns:
            Dict[str, Any]: Agent 返回的响应字典。
        """
        return self._request("GET", "/bluetooth/connected")

    def bluetooth_get_paired(self) -> Dict[str, Any]:
        """请求 Agent 获取系统已配对的蓝牙设备列表。

        Returns:
            Dict[str, Any]: Agent 返回的响应字典。
        """
        return self._request("GET", "/bluetooth/paired")

    # ========== 统一 Device 接口 ==========
    def play(self, url: str) -> tuple[int, str]:
        """通过 Agent 播放媒体文件。

        Args:
            url (str): 媒体文件的路径或 URL。

        Returns:
            tuple[int, str]: (code, msg)。code=0 表示成功。
        """
        # DeviceAgent 需要设备地址，从初始化时的 base_url 中提取 或者使用默认的蓝牙设备地址
        data = {"file_path": url}
        result = self._request("POST", "/media/play", json_data=data)
        code = result.get("code", -1)
        msg = result.get("msg", "未知错误")
        return (code, msg)

    def stop(self) -> tuple[int, str]:
        """通过 Agent 停止播放。

        Returns:
            tuple[int, str]: (code, msg)。code=0 表示成功。
        """
        result = self._request("POST", "/media/stop")
        code = result.get("code", -1)
        msg = result.get("msg", "未知错误")
        return (code, msg)

    def get_status(self) -> tuple[int, dict]:
        """通过 Agent 获取媒体播放状态。

        Returns:
            tuple[int, dict]: (code, status_dict)。code=0 表示成功。
                status_dict 包含 state, status, track, duration, position 等信息。
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

    def get_volume(self) -> int | None:
        """获取设备音量。

        尝试从 Agent 的状态接口获取音量信息，如果不支持则返回 None。

        Returns:
            int | None: 音量值（0-100），如果不支持则返回 None
        """
        try:
            # 尝试从状态接口获取音量
            code, status = self.get_status()
            if code == 0 and isinstance(status, dict):
                volume = status.get("volume")
                if volume is not None:
                    try:
                        volume_int = int(volume)
                        # 确保音量在有效范围内
                        if 0 <= volume_int <= 100:
                            return volume_int
                    except (TypeError, ValueError):
                        pass

            # 尝试直接调用音量接口（如果 Agent 支持）
            result = self._request("GET", "/media/volume")
            if result.get("code") == 0:
                data = result.get("data", {})
                volume = data.get("volume")
                if volume is not None:
                    try:
                        volume_int = int(volume)
                        if 0 <= volume_int <= 100:
                            return volume_int
                    except (TypeError, ValueError):
                        pass
        except Exception as e:
            log.debug(f"[DeviceAgent] Get volume error: {e}")

        # 设备不支持音量控制
        return None

    def set_volume(self, volume: int) -> bool:
        """设置设备音量。

        Args:
            volume (int): 目标音量值（0-100）

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        # 验证音量范围
        if not isinstance(volume, int) or volume < 0 or volume > 100:
            log.warning(f"[DeviceAgent] Invalid volume value: {volume}")
            return False

        try:
            # 尝试调用音量设置接口
            result = self._request("POST", "/media/volume", json_data={"volume": volume})
            if result.get("code") == 0:
                return True
            else:
                log.debug(f"[DeviceAgent] Set volume failed: {result.get('msg', '未知错误')}")
                return False
        except Exception as e:
            log.debug(f"[DeviceAgent] Set volume error: {e}")
            return False

    # ========== Agent 接口 ==========

    def mock(self, action: str, key: Optional[str] = None, value: Optional[str] = None) -> Dict[str, Any]:
        """请求 Agent 模拟一个设备操作。

        Args:
            action (str): 操作类型 (例如, "keyboard")。
            key (Optional[str]): 操作的键。
            value (Optional[str]): 操作的值。

        Returns:
            Dict[str, Any]: Agent 返回的响应字典。
        """
        if action == "keyboard":
            # 向 agent 的 /keyboard/mock 发送 key 和 value
            json_data = {}
            if key is not None:
                json_data["key"] = key
            if value is not None:
                json_data["value"] = value
            return self._request("POST", "/keyboard/mock", json_data=json_data)
        else:
            return {"code": -1, "msg": f"不支持的 action: {action}"}
