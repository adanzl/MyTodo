"""
Device Agent HTTP 客户端
用于通过内网调用 device_agent 服务的接口
"""
import requests
from typing import Optional, Dict, Any
from core.log_config import root_logger
from .config import DEVICE_AGENT_BASE_URL, DEVICE_AGENT_TIMEOUT

log = root_logger()


class DeviceAgentClient:
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
    
    # ========== 播放列表相关接口 ==========
    
    def playlist_update(self, playlist: list, device_address: Optional[str] = None) -> Dict[str, Any]:
        """
        更新播放列表
        :param playlist: 播放列表（文件路径列表）
        :param device_address: 蓝牙设备地址（可选）
        :return: 更新结果
        """
        data = {"playlist": playlist}
        if device_address:
            data["device_address"] = device_address
        return self._request("POST", "/playlist/update", json_data=data)
    
    def playlist_status(self) -> Dict[str, Any]:
        """
        获取播放列表状态
        :return: 播放列表状态
        """
        return self._request("GET", "/playlist/status")
    
    def playlist_play(self) -> Dict[str, Any]:
        """
        播放当前播放列表中的歌曲
        :return: 播放结果
        """
        return self._request("POST", "/playlist/play")
    
    def playlist_play_next(self) -> Dict[str, Any]:
        """
        播放下一首歌曲
        :return: 播放结果
        """
        return self._request("POST", "/playlist/playNext")
    
    def playlist_stop(self) -> Dict[str, Any]:
        """
        停止播放列表播放
        :return: 停止结果
        """
        # 播放列表的停止实际上就是停止媒体播放
        return self._request("POST", "/media/stop")
    
    # ========== Cron 定时任务相关接口 ==========
    
    def cron_get_status(self) -> Dict[str, Any]:
        """
        获取 Cron 定时任务状态
        :return: Cron 状态
        """
        return self._request("GET", "/cron/status")
    
    def cron_update(self, enabled: Optional[bool] = None, 
                    expression: Optional[str] = None, 
                    command: Optional[str] = None) -> Dict[str, Any]:
        """
        更新 Cron 定时任务配置
        :param enabled: 是否启用
        :param expression: Cron 表达式（格式: 分 时 日 月 周）
        :param command: 要执行的命令
        :return: 更新结果
        """
        data = {}
        if enabled is not None:
            data["enabled"] = enabled
        if expression is not None:
            data["expression"] = expression
        if command is not None:
            data["command"] = command
        return self._request("POST", "/cron/update", json_data=data)


# 全局客户端实例
_client_instance: Optional[DeviceAgentClient] = None


def get_device_agent_client() -> DeviceAgentClient:
    """
    获取全局 Device Agent 客户端实例（单例模式）
    :return: DeviceAgentClient 实例
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = DeviceAgentClient()
    return _client_instance

