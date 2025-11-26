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
    import ssdp
except ImportError:
    upnpclient = None
    ssdp = None

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
    if not (upnpclient and ssdp):
        return []

    try:
        log.info(f"[DLNA] Starting scan (timeout: {timeout}s)")
        device_list = []
        responses = ssdp.discover("urn:schemas-upnp-org:service:AVTransport:1", timeout=timeout)

        for resp in responses:
            try:
                device = upnpclient.Device(resp.location)
                device_list.append(_device_to_dict(device))
            except Exception as e:
                log.warning(f"[DLNA] Error processing {resp.location}: {e}")

        log.info(f"[DLNA] Found {len(device_list)} devices")
        return device_list
    except Exception as e:
        log.error(f"[DLNA] Scan error: {e}")
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
