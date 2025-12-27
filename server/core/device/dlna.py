'''
dlna设备管理
'''
import traceback
from typing import Dict, List
from urllib.parse import urlparse

import upnpclient
from ssdpy import SSDPClient

from core.log_config import root_logger
from core.utils import convert_to_http_url

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


def scan_devices_sync(timeout: float = 5.0) -> List[Dict]:
    """扫描DLNA设备（同步，gevent 环境友好）"""
    if not upnpclient or not SSDPClient:
        log.warning("[DLNA] upnpclient or SSDPClient not available")
        return []

    try:
        log.info(f"[DLNA] Starting scan (timeout: {timeout}s)")
        device_list = []
        locations = set()

        # 使用 SSDPClient 搜索设备
        if SSDPClient:
            try:
                client = SSDPClient()
                mx_value = min(max(int(timeout), 1), 5)  # 限制在 1-5 秒之间
                responses = client.m_search(st="urn:schemas-upnp-org:device:MediaRenderer:1", mx=mx_value)
                for resp in responses:
                    location = resp.get("location") or resp.get("LOCATION")
                    if location:
                        locations.add(location)
                log.info(f"[DLNA] Found {len(locations)} device locations via ssdpy")
            except Exception as e:
                log.warning(f"[DLNA] SSDPClient search failed: {e}")

        # 如果 SSDPClient 没有找到设备，尝试使用 upnpclient.discover
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

        log.info(f"[DLNA] Found {len(device_list)} devices")
        return device_list
    except Exception as e:
        log.error(f"[DLNA] Scan error: {e}")
        log.error(traceback.format_exc())
        return []


class DlnaDev:
    """DLNA 设备控制类"""

    def __init__(self, location: str, name: str = ""):
        """
        初始化 DLNA 设备
        :param location: 设备描述文档的完整 URL
        """
        self.location = location
        self._device = None
        self._av_transport = None
        self.name = name or location

    def _get_device(self):
        """获取 upnpclient.Device 对象"""
        if self._device is None:
            try:
                if not self.location or not (self.location.startswith('http://') or self.location.startswith('https://')):
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

    def _get_transport_info(self) -> tuple[int, dict]:
        """获取传输状态信息"""
        av_transport = self._get_av_transport()
        if av_transport is None:
            return -1, {"error": "AVTransport service not available"}

        try:
            result = av_transport.GetTransportInfo(InstanceID=0)
            return 0, {
                "transport_state": result.get('CurrentTransportState', 'UNKNOWN'),
                "transport_status": result.get('CurrentTransportStatus', 'UNKNOWN'),
                "speed": result.get('CurrentSpeed', '1')
            }
        except Exception as e:
            log.error(f"[DlnaDev] Failed to get transport info: {e}")
            return -1, {"error": str(e)}

    def _get_position_info(self) -> tuple[int, dict]:
        """获取播放位置信息"""
        av_transport = self._get_av_transport()
        if av_transport is None:
            return -1, {"error": "AVTransport service not available"}

        try:
            result = av_transport.GetPositionInfo(InstanceID=0)
            track = result.get('Track', '0')
            return 0, {
                "track": track,
                "duration": result.get('TrackDuration', '00:00:00'),
                "rel_time": result.get('RelTime', '00:00:00')
            }
        except Exception as e:
            log.error(f"[DlnaDev] Failed to get position info: {e}")
            return -1, {"error": str(e)}

    def play(self, url: str) -> tuple[int, str]:
        """
        播放媒体文件【OUT】
        :param url: 媒体文件 URL 可以是 http://、file:// 或本地文件路径
        :return: (错误码, 消息)
        """
        av_transport = self._get_av_transport()
        if av_transport is None:
            return -1, "AVTransport service not available"

        media_url = convert_to_http_url(url)

        try:
            av_transport.SetAVTransportURI(InstanceID=0, CurrentURI=media_url, CurrentURIMetaData="")
            log.info(f"[DlnaDev] Set media URI: {media_url} (original: {url})")
        except Exception as e:
            log.error(f"[DlnaDev] Failed to set URI: {e}")
            return -1, f"Failed to set URI: {str(e)}"

        try:
            av_transport.Play(InstanceID=0, Speed="1")
            log.info(f"[DlnaDev] Play started: {media_url}")
            return 0, "播放成功"
        except Exception as e:
            log.error(f"[DlnaDev] Failed to play: {e}")
            return -1, f"播放失败: {str(e)}"

    def stop(self) -> tuple[int, str]:
        """停止播放【OUT】"""
        av_transport = self._get_av_transport()
        if av_transport is None:
            return -1, "AVTransport service not available"

        try:
            # 使用 gevent Timeout 包装 UPnP 调用，避免阻塞
            from gevent import Timeout
            with Timeout(5.0):  # 5秒超时
                av_transport.Stop(InstanceID=0)
            log.info(f"[DlnaDev] Stop playback {self.name}")
            return 0, "停止成功"
        except Timeout:
            log.warning(f"[DlnaDev] Stop timeout after 5 seconds for {self.name}")
            return -1, "停止超时：设备无响应"
        except Exception as e:
            log.error(f"[DlnaDev] Stop error: {e}")
            return -1, f"停止失败: {str(e)}"

    def get_status(self) -> tuple[int, dict]:
        """获取播放状态信息（合并 transport_info 和 position_info）"""
        transport_code, transport_info = self._get_transport_info()
        position_code, position_info = self._get_position_info()

        if transport_code != 0 and position_code != 0:
            return -1, {"error": "无法获取播放状态信息"}

        status = {
            "state": transport_info.get("transport_state", "UNKNOWN") if transport_code == 0 else "UNKNOWN",
            "status": transport_info.get("transport_status", "UNKNOWN") if transport_code == 0 else "ERROR",
            "track": int(position_info.get("track", 0)) if position_code == 0 and position_info.get("track") else 0,
            "duration": position_info.get("duration", "00:00:00") if position_code == 0 else "00:00:00",
            "position": position_info.get("rel_time", "00:00:00") if position_code == 0 else "00:00:00"
        }

        return_code = 0 if (transport_code == 0 or position_code == 0) else -1
        return return_code, status
