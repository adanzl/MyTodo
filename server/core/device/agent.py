"""
Device Agent HTTP 客户端
用于通过内网调用 device_agent 服务的接口
"""
import os
import requests
from typing import Optional, Dict, Any
from core.log_config import root_logger
log = root_logger()

DEVICE_AGENT_HOST = os.getenv('DEVICE_AGENT_HOST', '192.168.50.184')
DEVICE_AGENT_PORT = os.getenv('DEVICE_AGENT_PORT', '8000')

# 完整的服务URL
DEVICE_AGENT_BASE_URL = f"http://{DEVICE_AGENT_HOST}:{DEVICE_AGENT_PORT}"

# 请求超时时间（秒）
DEVICE_AGENT_TIMEOUT = 30

class DeviceAgent:
    """Device Agent HTTP 客户端"""
    
    def __init__(self, base_url: str = None, timeout: int = None):
        """
        初始化客户端
        :param base_url: 服务基础URL，默认使用配置中的值
        :param timeout: 请求超时时间（秒），默认使用配置中的值
        """
        self.base_url = base_url or DEVICE_AGENT_BASE_URL
        self.timeout = timeout or DEVICE_AGENT_TIMEOUT
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
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
            
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.timeout
            )
            
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
    
    # ========== 媒体相关接口 ==========
    
    def media_play(self, file_path: str, device_address: Optional[str] = None) -> Dict[str, Any]:
        """
        播放音频文件
        :param file_path: 文件路径
        :param device_address: 蓝牙设备地址（可选）
        :return: 播放结果
        """
        data = {"file_path": file_path}
        if device_address:
            data["device_address"] = device_address
        return self._request("POST", "/media/play", json_data=data)
    
    def media_stop(self) -> Dict[str, Any]:
        """
        停止当前播放
        :return: 停止结果
        """
        return self._request("POST", "/media/stop")

    # ========== 统一设备接口 ==========
    
    def play(self, url: str) -> tuple[int, str]:
        """
        播放媒体文件（统一接口）
        :param url: 媒体文件路径或URL
        :return: (错误码, 消息)
        """
        # DeviceAgent 需要设备地址，从初始化时的 base_url 中提取
        # 或者使用默认的蓝牙设备地址
        result = self.media_play(url)
        code = result.get("code", -1)
        msg = result.get("msg", "未知错误")
        return (code, msg)
    
    def stop(self) -> tuple[int, str]:
        """
        停止播放（统一接口）
        :return: (错误码, 消息)
        """
        result = self.media_stop()
        code = result.get("code", -1)
        msg = result.get("msg", "未知错误")
        return (code, msg)
    
    def get_transport_info(self) -> tuple[int, dict]:
        """
        获取传输状态信息（统一接口）
        :return: (错误码, 状态字典)
        """
        # DeviceAgent 可能不支持获取传输状态，返回默认值
        # 可以通过调用 device_agent 的 /media/status 接口来实现（如果存在）
        try:
            # 尝试调用状态接口（如果存在）
            result = self._request("GET", "/media/status")
            if result.get("code") == 0:
                data = result.get("data", {})
                return (0, {
                    "transport_state": data.get("is_playing", False) and "PLAYING" or "STOPPED",
                    "transport_status": "OK",
                    "speed": "1"
                })
        except Exception:
            pass
        
        # 如果接口不存在，返回未知状态
        return (-1, {"error": "设备不支持获取传输状态"})
    
    def get_position_info(self) -> tuple[int, dict]:
        """
        获取播放位置信息（统一接口）
        :return: (错误码, 位置字典)
        """
        # DeviceAgent 可能不支持获取位置信息，返回默认值
        # 可以通过调用 device_agent 的 /media/position 接口来实现（如果存在）
        try:
            result = self._request("GET", "/media/position")
            if result.get("code") == 0:
                data = result.get("data", {})
                return (0, {
                    "track": "0",
                    "track_duration": data.get("duration", "00:00:00"),
                    "rel_time": data.get("position", "00:00:00"),
                    "abs_time": "00:00:00"
                })
        except Exception:
            pass
        
        # 如果接口不存在，返回未知状态
        return (-1, {"error": "设备不支持获取位置信息"})
    
    def is_playing(self) -> bool:
        """
        检查是否正在播放（统一接口）
        :return: True 如果正在播放，False 否则
        """
        code, info = self.get_transport_info()
        if code != 0:
            return False
        transport_state = info.get("transport_state", "").upper()
        return transport_state == "PLAYING"
    

