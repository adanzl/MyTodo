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
                # 搜索媒体渲染器设备（MediaRenderer）- DLNA 播放设备
                # m_search 只接受 st 和 mx 参数，mx 是最大等待时间（建议 1-5 秒）
                mx_value = min(max(int(timeout), 1), 5)  # 限制在 1-5 秒之间
                responses = client.m_search(st="urn:schemas-upnp-org:device:MediaRenderer:1", mx=mx_value)
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
    """DLNA 设备控制类"""

    def __init__(self, location: str):
        """
        初始化 DLNA 设备
        :param location: 设备描述文档的完整 URL
        """
        self.location = location
        self._device = None
        self._av_transport = None

    def _get_device(self):
        """获取 upnpclient.Device 对象"""
        if self._device is None:
            try:
                if not self.location or not (self.location.startswith('http://')
                                             or self.location.startswith('https://')):
                    log.error(f"[DlnaDev] Invalid location URL: {self.location}")
                    return None

                self._device = upnpclient.Device(self.location)
                log.info(f"[DlnaDev] Connected to device: {self._device.friendly_name} at {self.location}")
            except Exception as e:
                log.error(f"[DlnaDev] Failed to connect to device {self.location}: {e}")
                return None
        return self._device

    def _get_av_transport(self):
        """获取 AVTransport 服务"""
        device = self._get_device()
        if device is None:
            return None

        if self._av_transport is None:
            try:
                # 查找 AVTransport 服务
                for service in device.services:
                    if 'AVTransport' in service.service_type:
                        self._av_transport = service
                        log.debug(f"[DlnaDev] Found AVTransport service: {service.service_id}")
                        break

                if self._av_transport is None:
                    log.error("[DlnaDev] AVTransport service not found")
            except Exception as e:
                log.error(f"[DlnaDev] Error getting AVTransport: {e}")

        return self._av_transport

    def play(self, url: str) -> tuple[int, str]:
        """
        播放媒体文件
        :param url: 媒体文件 URL（可以是 http:// 或 file:// 路径）
        :return: (错误码, 消息)
        """
        try:
            av_transport = self._get_av_transport()
            if av_transport is None:
                return -1, "AVTransport service not available"

            # 设置媒体 URI
            try:
                av_transport.SetAVTransportURI(InstanceID=0, CurrentURI=url, CurrentURIMetaData="")
                log.info(f"[DlnaDev] Set media URI: {url}")
            except Exception as e:
                log.error(f"[DlnaDev] Failed to set URI: {e}")
                return -1, f"Failed to set URI: {str(e)}"

            # 开始播放
            try:
                av_transport.Play(InstanceID=0, Speed="1")
                log.info(f"[DlnaDev] Play started: {url}")
                return 0, "播放成功"
            except Exception as e:
                log.error(f"[DlnaDev] Failed to play: {e}")
                return -1, f"播放失败: {str(e)}"
        except Exception as e:
            log.error(f"[DlnaDev] Play error: {e}")
            return -1, f"播放异常: {str(e)}"

    def stop(self) -> tuple[int, str]:
        """
        停止播放
        :return: (错误码, 消息)
        """
        try:
            av_transport = self._get_av_transport()
            if av_transport is None:
                return -1, "AVTransport service not available"

            av_transport.Stop(InstanceID=0)
            log.info(f"[DlnaDev] Stop playback")
            return 0, "停止成功"
        except Exception as e:
            log.error(f"[DlnaDev] Stop error: {e}")
            return -1, f"停止失败: {str(e)}"
