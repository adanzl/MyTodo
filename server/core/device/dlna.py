'''
dlna设备管理
'''
from typing import Dict, List
from core.log_config import root_logger
import upnpclient
import ssdp

log = root_logger()


class DlnaDev:
    """Dlna设备类"""

    def __init__(self, address: str):
        self.address = address
        log.info(f"[DlnaDev] init {self.address}")

    def play(self, file_path: str) -> tuple[int, str]:
        return 0, "播放成功"

    def stop(self) -> tuple[int, str]:
        return 0, "停止成功"


class DlnaMgr:
    """DLNA设备管理器"""

    def __init__(self):
        log.info("[DLNA] DlnaMgr init")
        self.devices: Dict[str, Dict] = {}  # address -> device info

    @staticmethod
    async def scan_devices(timeout: float = 5.0) -> List[Dict]:
        """
        扫描DLNA设备
        :param timeout: 扫描超时时间（秒）
        :return: 设备列表
        """
        try:
            log.info(f"[DLNA] Starting scan (timeout: {timeout}s)")
            device_list = []
            # 搜索 UPnP AVTransport 服务（DLNA 播放设备必带）
            responses = ssdp.discover("urn:schemas-upnp-org:service:AVTransport:1", timeout=timeout)
            for resp in responses:
                # 通过设备描述 URL 获取设备详情
                device = upnpclient.Device(resp.location)
                device_list.append(device)
                log.inifo(f"发现设备: {device.friendly_name} (URL: {resp.location})")
            log.info(f"[DLNA] Found {len(device_list)} devices")
            return device_list
        except Exception as e:
            log.error(f"[DLNA] Scan error: {e}")
            return []
