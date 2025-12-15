'''
dlna设备管理
'''
import asyncio
import concurrent.futures
import json
import os
from typing import Dict, List
from urllib.parse import urlparse
from core.log_config import root_logger
from core.async_util import run_async
from core.utils import convert_to_http_url

import upnpclient
from ssdpy import SSDPClient

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

    def _get_transport_info(self) -> tuple[int, dict]:
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
                # log.info(f"[DlnaDev] Transport info: {json.dumps(info)}")
                return 0, info
            except Exception as e:
                log.error(f"[DlnaDev] Failed to get transport info: {e}")
                return -1, {"error": str(e)}
        except Exception as e:
            log.error(f"[DlnaDev] GetTransportInfo error: {e}")
            return -1, {"error": str(e)}

    def _get_position_info(self) -> tuple[int, dict]:
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
                track = result.get('Track', '0')  # 当前播放的「曲目索引」（仅多曲目播放时有效，如播放播放列表），单文件播放时通常为 1。
                track_duration = result.get('TrackDuration', '00:00:00')  # 当前曲目的「总时长」
                rel_time = result.get('RelTime', '00:00:00')  # 相对时间（已播放时间）

                info = {
                    "track": track,
                    "duration": track_duration,  # 总时长，格式如 "00:03:45"
                    "rel_time": rel_time,  # 已播放时长，格式如 "00:01:30"
                }
                log.debug(f"[DlnaDev] Position info: {info}")
                return 0, info
            except Exception as e:
                log.error(f"[DlnaDev] Failed to get position info: {e}")
                return -1, {"error": str(e)}
        except Exception as e:
            log.error(f"[DlnaDev] GetPositionInfo error: {e}")
            return -1, {"error": str(e)}

    # ========== 统一设备接口 ==========
    def play(self, url: str) -> tuple[int, str]:
        """
        播放媒体文件【OUT】
        :param url: 媒体文件 URL 可以是 http://、file:// 或本地文件路径
        :return: (错误码, 消息)
        """
        try:
            av_transport = self._get_av_transport()
            if av_transport is None:
                return -1, "AVTransport service not available"

            # 转换本地文件路径为 HTTP URL
            media_url = convert_to_http_url(url)

            # 设置媒体 URI
            try:
                av_transport.SetAVTransportURI(InstanceID=0, CurrentURI=media_url, CurrentURIMetaData="")
                log.info(f"[DlnaDev] Set media URI: {media_url} (original: {url})")
            except Exception as e:
                log.error(f"[DlnaDev] Failed to set URI: {e}")
                return -1, f"Failed to set URI: {str(e)}"

            # 开始播放
            try:
                av_transport.Play(InstanceID=0, Speed="1")
                log.info(f"[DlnaDev] Play started: {media_url}")
            except Exception as e:
                log.error(f"[DlnaDev] Failed to play: {e}")
                return -1, f"播放失败: {str(e)}"

            return 0, "播放成功"
        except Exception as e:
            log.error(f"[DlnaDev] Play error: {e}")
            return -1, f"播放异常: {str(e)}"

    def stop(self) -> tuple[int, str]:
        """
        停止播放【OUT】
        :return: (错误码, 消息)
        """
        try:
            av_transport = self._get_av_transport()
            if av_transport is None:
                return -1, "AVTransport service not available"

            av_transport.Stop(InstanceID=0)
            log.info(f"[DlnaDev] Stop playback {self.name}")
            return 0, "停止成功"
        except Exception as e:
            log.error(f"[DlnaDev] Stop error: {e}")
            return -1, f"停止失败: {str(e)}"

    def get_status(self) -> tuple[int, dict]:
        """
        获取播放状态信息（合并 transport_info 和 position_info）
        :return: (错误码, 状态字典) 格式: {'state', 'status', 'track', 'duration', 'position'}
        """
        transport_code, transport_info = self._get_transport_info()
        position_code, position_info = self._get_position_info()

        # 如果两个都失败，返回错误
        if transport_code != 0 and position_code != 0:
            return -1, {"error": "无法获取播放状态信息"}

        # 构建统一格式的状态字典
        status = {}

        # 从 transport_info 获取 state 和 status
        if transport_code == 0:
            status["state"] = transport_info.get("transport_state", "UNKNOWN")  # PLAYING, STOPPED, etc.
            status["status"] = transport_info.get("transport_status", "UNKNOWN")  # OK, ERROR_OCCURRED, etc.
        else:
            status["state"] = "UNKNOWN"
            status["status"] = "ERROR"

        # 从 position_info 获取 track, duration, position
        if position_code == 0:
            status["track"] = int(position_info.get("track", 0)) if position_info.get("track") else 0
            status["duration"] = position_info.get("track_duration", "00:00:00")
            status["position"] = position_info.get("rel_time", "00:00:00")
        else:
            status["track"] = 0
            status["duration"] = "00:00:00"
            status["position"] = "00:00:00"

        # 如果至少有一个成功，返回成功
        return_code = 0 if (transport_code == 0 or position_code == 0) else -1
        return return_code, status
