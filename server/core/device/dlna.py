'''
dlna设备管理
'''
import asyncio
import concurrent.futures
import os
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
        :param url: 媒体文件 URL（可以是 http://、file:// 或本地文件路径）
        :return: (错误码, 消息)
        """
        try:
            av_transport = self._get_av_transport()
            if av_transport is None:
                return -1, "AVTransport service not available"

            # 转换本地文件路径为 HTTP URL
            media_url = self._convert_to_http_url(url)

            # 设置媒体 URI
            try:
                av_transport.SetAVTransportURI(InstanceID=0, CurrentURI=media_url, CurrentURIMetaData="")
                log.info(f"[DlnaDev] Set media URI: {media_url} (original: {url})")
            except Exception as e:
                log.error(f"[DlnaDev] Failed to set URI: {e}")
                return -1, f"Failed to set URI: {str(e)}"

            result = av_transport.GetSupportedPlayModes(InstanceID=0)
            log.info(f"[DlnaDev] 设备支持的播放模式：{result['SupportedPlayModes']}")
            # 设置播放模式为 NORMAL（禁用单曲循环）
            # 注意：在设置 URI 之后、播放之前设置播放模式，这样更可靠
            try:
                if hasattr(av_transport, 'SetPlayMode'):
                    av_transport.SetPlayMode(InstanceID=0, NewPlayMode='NORMAL')
                    log.info(f"[DlnaDev] Set play mode to NORMAL (disable repeat)")
                else:
                    log.debug(f"[DlnaDev] SetPlayMode not available, device may not support it")
            except Exception as e:
                # SetPlayMode 是可选的，某些设备可能不支持，不影响播放
                log.warning(f"[DlnaDev] SetPlayMode failed (may not be supported): {e}")

            # 开始播放
            try:
                av_transport.Play(InstanceID=0, Speed="1")
                log.info(f"[DlnaDev] Play started: {media_url}")
            except Exception as e:
                log.error(f"[DlnaDev] Failed to play: {e}")
                return -1, f"播放失败: {str(e)}"

            # 播放后再次设置播放模式（某些设备需要在播放后设置才生效）
            try:
                if hasattr(av_transport, 'SetPlayMode'):
                    av_transport.SetPlayMode(InstanceID=0, NewPlayMode='NORMAL')
                    log.debug(f"[DlnaDev] Set play mode to NORMAL after play (disable repeat)")
            except Exception as e:
                log.debug(f"[DlnaDev] SetPlayMode after play failed: {e}")

            return 0, "播放成功"
        except Exception as e:
            log.error(f"[DlnaDev] Play error: {e}")
            return -1, f"播放异常: {str(e)}"

    def _convert_to_http_url(self, url: str) -> str:
        """
        将本地文件路径转换为 HTTP URL
        :param url: 本地文件路径（如 /mnt/ext_base/audio/xxx.mp3）或已经是 HTTP URL
        :return: HTTP URL
        """
        # 如果已经是 HTTP/HTTPS URL，直接返回
        if url.startswith('http://') or url.startswith('https://'):
            return url

        # 如果是 file:// URL，提取路径
        if url.startswith('file://'):
            url = url[7:]  # 移除 file:// 前缀

        # 如果是本地绝对路径（以 / 开头），转换为 HTTP URL
        if url.startswith('/') and os.path.exists(url):
            try:
                # 动态导入以避免循环依赖
                from core.api.media_routes import get_media_url
                return get_media_url(url)
            except ImportError:
                log.warning("[DlnaDev] Cannot import get_media_url, using original URL")
                return url

        # 其他情况直接返回（可能是相对路径或其他格式）
        return url

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

    def get_transport_info(self) -> tuple[int, dict]:
        """
        获取传输状态信息
        :return: (错误码, 状态字典) 状态字典包含: transport_state, transport_status, speed
        """
        try:
            av_transport = self._get_av_transport()
            if av_transport is None:
                return -1, {"error": "AVTransport service not available"}

            try:
                result = av_transport.GetTransportInfo(InstanceID=0)
                transport_state = result.get('CurrentTransportState', 'UNKNOWN')
                transport_status = result.get('CurrentTransportStatus', 'UNKNOWN')
                speed = result.get('CurrentSpeed', '1')

                info = {
                    "transport_state": transport_state,  # PLAYING, STOPPED, PAUSED_PLAYBACK, etc.
                    "transport_status": transport_status,  # OK, ERROR_OCCURRED, etc.
                    "speed": speed
                }
                log.debug(f"[DlnaDev] Transport info: {info}")
                return 0, info
            except Exception as e:
                log.error(f"[DlnaDev] Failed to get transport info: {e}")
                return -1, {"error": str(e)}
        except Exception as e:
            log.error(f"[DlnaDev] GetTransportInfo error: {e}")
            return -1, {"error": str(e)}

    def get_position_info(self) -> tuple[int, dict]:
        """
        获取播放位置信息
        :return: (错误码, 位置字典) 位置字典包含: track, track_duration, rel_time, abs_time
        """
        try:
            av_transport = self._get_av_transport()
            if av_transport is None:
                return -1, {"error": "AVTransport service not available"}

            try:
                result = av_transport.GetPositionInfo(InstanceID=0)
                track = result.get('Track', '0')
                track_duration = result.get('TrackDuration', '00:00:00')
                rel_time = result.get('RelTime', '00:00:00')  # 相对时间（已播放时间）
                abs_time = result.get('AbsTime', '00:00:00')  # 绝对时间

                info = {
                    "track": track,
                    "track_duration": track_duration,  # 总时长，格式如 "00:03:45"
                    "rel_time": rel_time,  # 已播放时长，格式如 "00:01:30"
                    "abs_time": abs_time
                }
                log.debug(f"[DlnaDev] Position info: {info}")
                return 0, info
            except Exception as e:
                log.error(f"[DlnaDev] Failed to get position info: {e}")
                return -1, {"error": str(e)}
        except Exception as e:
            log.error(f"[DlnaDev] GetPositionInfo error: {e}")
            return -1, {"error": str(e)}
