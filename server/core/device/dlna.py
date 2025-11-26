'''
dlna设备管理
'''
import asyncio
import concurrent.futures
from typing import Dict, List
from urllib.parse import urlparse
from core.log_config import root_logger
from core.async_utils import run_async

try:
    import upnpclient
    from ssdpy import SSDPClient
except ImportError:
    upnpclient = None
    SSDPClient = None

log = root_logger()


def _device_to_dict(device) -> Dict:
    """将 upnpclient.Device 对象转换为字典"""
    try:
        location = getattr(device, 'location', '')
        address = urlparse(location).hostname if location else ''

        return {
            "address": address,
            "name": getattr(device, 'friendly_name', '') or address or 'Unknown',
            "device_type": getattr(device, 'device_type', ''),
            "manufacturer": getattr(device, 'manufacturer', ''),
            "model_name": getattr(device, 'model_name', ''),
            "location": location,
        }
    except Exception as e:
        log.error(f"[DLNA] Error converting device: {e}")
        return {
            "address": "",
            "name": "Unknown",
            "device_type": "",
            "manufacturer": "",
            "model_name": "",
            "location": ""
        }


async def scan_devices(timeout: float = 5.0) -> List[Dict]:
    """扫描DLNA设备"""
    if not upnpclient or not SSDPClient:
        log.warning("[DLNA] upnpclient or SSDPClient not available")
        return []

    try:
        log.info(f"[DLNA] Starting scan (timeout: {timeout}s)")
        device_list = []
        locations = set()  # 用于去重

        if SSDPClient:
            try:
                client = SSDPClient()
                # 搜索 UPnP AVTransport 服务（DLNA 播放设备）
                responses = client.m_search(st="urn:schemas-upnp-org:service:AVTransport:1", timeout=int(timeout), mx=int(timeout))
                for resp in responses:
                    location = resp.get("location") or resp.get("LOCATION")
                    if location and location not in locations:
                        locations.add(location)
                log.info(f"[DLNA] Found {len(locations)} device locations via ssdpy")
            except Exception as e:
                log.warning(f"[DLNA] SSDPClient search failed: {e}")


        # 尝试使用 upnpclient 的搜索功能（如果可用）
        if not locations and hasattr(upnpclient, 'discover'):
            try:
                devices = upnpclient.discover(timeout=int(timeout))
                for device in devices:
                    if hasattr(device, 'location'):
                        locations.add(device.location)
                log.info(f"[DLNA] Found {len(locations)} device locations via upnpclient.discover")
            except Exception as e:
                log.warning(f"[DLNA] upnpclient.discover failed: {e}")

        # 处理发现的设备
        for location in locations:
            try:
                device = upnpclient.Device(location)
                device_dict = _device_to_dict(device)
                device_list.append(device_dict)
                log.info(f"发现设备: {device_dict['name']} (地址: {device_dict['address']})")
            except Exception as e:
                log.warning(f"[DLNA] Error processing {location}: {e}")
                continue

        log.info(f"[DLNA] Found {len(device_list)} devices")
        return device_list
    except Exception as e:
        log.error(f"[DLNA] Scan error: {e}")
        import traceback
        log.error(traceback.format_exc())
        return []


def scan_devices_sync(timeout: float = 5.0) -> List[Dict]:
    """同步扫描DLNA设备"""
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async, scan_devices(timeout))
            return future.result(timeout=timeout + 5.0)
    except RuntimeError:
        return run_async(scan_devices(timeout))
    except Exception as e:
        log.error(f"[DLNA] Scan error: {e}")
        return []


class DlnaDev:

    def __init__(self, address: str):
        self.address = address

    def play(self, url: str) -> tuple[int, str]:
        return 0, "ok"

    def stop(self) -> tuple[int, str]:
        return 0, "ok"

    def play_next(self) -> tuple[int, str]:
        return 0, "ok"

    def play_prev(self) -> tuple[int, str]:
        return 0, "ok"
