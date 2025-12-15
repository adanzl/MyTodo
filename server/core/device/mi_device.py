'''
小米设备管理
'''
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, List

from aiohttp import ClientSession
from miservice import MiAccount, MiNAService

from core.utils import run_async, convert_to_http_url, format_time_str
from core.log_config import root_logger

log = root_logger()

# 从环境变量读取小米账号信息，如果没有则使用默认值
DEFAULT_MI_USERNAME = os.getenv("MI_USER", "")
DEFAULT_MI_PASSWORD = os.getenv("MI_PASS", "")


def _device_to_dict(device) -> Dict:
    """将 Device 对象转换为字典"""
    try:
        return {
            "address": device.get('address', ''),
            "name": device.get('name', ''),
            "deviceID": device.get('deviceID', ''),
        }
    except Exception as e:
        log.error(f"[MiDevice] Error converting device: {e}")
        return {
            "address": "",
            "name": "Unknown",
            "deviceID": "",
        }


async def _get_device_did_async(username: str, password: str, device_id: str) -> tuple[int, str]:
    session = None
    try:
        session = ClientSession()
        account = MiAccount(session, username, password, os.path.join(str(Path.home()), ".mi.token"))
        mina_service = MiNAService(account)
        device_list = await mina_service.device_list()
        for device in device_list:
            if device['deviceID'] == device_id:
                return 0, device['miotDID']
    except Exception as e:
        log.error(f"[MiDevice] Get device did error: {e}")
    finally:
        if session:
            await session.close()
    return -1, "设备未找到"


class MiDevice:
    """小米设备管理"""
    scanning = False

    def __init__(self, address: str, username: str = None, password: str = None, name: str = ""):
        """
        初始化小米设备
        :param address: 设备ID或地址
        :param username: 小米账号用户名（可选，使用默认值）
        :param password: 小米账号密码（可选，使用默认值）
        """
        self.device_id = address  # 小米设备使用 deviceID 作为地址
        self.username = username or DEFAULT_MI_USERNAME
        self.password = password or DEFAULT_MI_PASSWORD
        self.name = name or address
        self.device_did = None

    @staticmethod
    async def scan_devices(username: str = None, password: str = None) -> List[Dict]:
        """扫描小米设备"""
        if MiDevice.scanning:
            log.warning("[MiDevice] Already scanning")
            return []

        username = username or DEFAULT_MI_USERNAME
        password = password or DEFAULT_MI_PASSWORD

        try:
            MiDevice.scanning = True
            log.info(f"[MiDevice] Starting scan")
            async with ClientSession() as session:
                account = MiAccount(
                    session,
                    username,
                    password,
                    os.path.join(str(Path.home()), ".mi.token"),
                )
                mina_service = MiNAService(account)
                result = await mina_service.device_list()
                device_list = [_device_to_dict(device) for device in result]
                log.info(f"[MiDevice] Found {len(device_list)} devices")
            return device_list

        except Exception as e:
            log.error(f"[MiDevice] Scan error: {e}")
            return []
        finally:
            MiDevice.scanning = False

    def _create_account(self, session: ClientSession) -> MiAccount:
        return MiAccount(
            session,
            self.username,
            self.password,
            os.path.join(str(Path.home()), ".mi.token"),
        )

    # ========== 统一设备接口 ==========
    def play(self, url: str) -> tuple[int, str]:
        """
        播放媒体文件【OUT】
        :param url: 媒体文件 URL (可以是 http://、file:// 或本地文件路径)
        :return: (错误码, 消息)
        """

        async def _play_async():
            session = None
            try:
                media_url = convert_to_http_url(url)
                # 获取 MiNAService 对象
                session = ClientSession()
                account = self._create_account(session)
                mina_service = MiNAService(account)
                await mina_service.play_by_url(self.device_id, media_url)
                # 设置循环播放为0（不循环），避免文件播放完成后自动重播导致重复播放
                await mina_service.player_set_loop(self.device_id, 0)
                return 0, "ok"
            except Exception as e:
                log.error(f"[MiDevice] Play error: {e}")
                return -1, f"播放失败: {str(e)}"
            finally:
                if session:
                    await session.close()

        try:
            return run_async(_play_async(), timeout=10.0)
        except Exception as e:
            log.error(f"[MiDevice] Play error: {e}")
            return -1, f"播放失败: {str(e)}"

    def stop(self) -> tuple[int, str]:
        """
        停止播放【OUT】
        :return: (错误码, 消息)
        """

        async def _stop_async():
            session = None
            try:
                # 获取 MiNAService 对象
                session = ClientSession()
                account = self._create_account(session)
                mina_service = MiNAService(account)
                await mina_service.player_pause(self.device_id)
                return 0, "ok"
            except Exception as e:
                log.error(f"[MiDevice] Stop error: {e}")
                return -1, f"停止失败: {str(e)}"
            finally:
                if session:
                    await session.close()

        try:
            return run_async(_stop_async(), timeout=10.0)
        except Exception as e:
            log.error(f"[MiDevice] Stop error: {e}")
            return -1, f"停止失败: {str(e)}"

    def get_status(self) -> tuple[int, dict]:
        """
        获取播放状态信息
        :return: (错误码, 状态字典) 格式: {'state', 'status', 'track', 'duration', 'position'}
        """

        async def _get_status_async():
            session = None
            try:
                # 获取 MiNAService 对象
                session = ClientSession()
                account = self._create_account(session)
                mina_service = MiNAService(account)
                ret = await mina_service.player_get_status(self.device_id)
                if ret['code'] != 0:
                    return -1, {"error": ret['message']}
                info = json.loads(ret['data']['info'])
                state = 'STOPPED' if info['status'] == 1 else 'PLAYING'
                play_song_detail = info['play_song_detail']
                duration = format_time_str(play_song_detail['duration'] /
                                           1000) if play_song_detail.get('duration') else '00:00:00'
                track_list = info.get('track_list', [])
                audio_id = play_song_detail.get('audio_id')
                position = play_song_detail.get('position', 0)  # 播放位置 单位：毫秒

                track = 0
                if audio_id and track_list:
                    track = track_list.index(audio_id) + 1

                return 0, {
                    "state": state,  # PLAYING, STOPPED
                    "status": 'OK',  # OK, ERROR
                    "track": track,  # 当前曲目索引（从1开始）
                    "duration": duration,  # 总时长，格式如 "00:03:45"
                    "position": format_time_str(position / 1000),  # 已播放时长，格式如 "00:01:30"
                }
            except Exception as e:
                log.error(f"[MiDevice] Get status error: {e}")
                return -1, {"error": f"获取播放状态信息失败: {str(e)}"}
            finally:
                if session:
                    await session.close()

        try:
            return run_async(_get_status_async(), timeout=5.0)
        except Exception as e:
            log.error(f"[MiDevice] Get status error: {e}")
            return -1, {"error": f"获取播放状态信息失败: {str(e)}"}

    # ========== 设备功能接口 ==========
    def get_volume(self) -> tuple[int, int]:
        """
        获取设备音量
        :return: (错误码, 音量)
        """

        async def _get_status_async():
            session = None
            try:
                # 获取 MiNAService 对象
                session = ClientSession()
                account = self._create_account(session)
                mina_service = MiNAService(account)
                ret = await mina_service.player_get_status(self.device_id)
                if ret['code'] != 0:
                    return -1, {"error": ret['message']}
                info = json.loads(ret['data']['info'])
                volume = info.get('volume', 0)

                return 0, volume

            except Exception as e:
                log.error(f"[MiDevice] Get volume error: {e}")
                return -1, -1
            finally:
                if session:
                    await session.close()

        try:
            return run_async(_get_status_async(), timeout=5.0)
        except Exception as e:
            log.error(f"[MiDevice] Get volume error: {e}")
            return -1, -1

    def set_volume(self, volume: int) -> tuple[int, str]:
        """
        设置设备音量
        :param volume: 音量
        :return: (错误码, 消息)
        """

        async def _set_volume_async():
            session = None
            try:
                # 获取 MiNAService 对象
                session = ClientSession()
                account = self._create_account(session)
                mina_service = MiNAService(account)
                await mina_service.player_set_volume(self.device_id, volume)
                return 0, "ok"
            except Exception as e:
                log.error(f"[MiDevice] Set volume error: {e}")
                return -1, f"设置音量失败: {str(e)}"
            finally:
                if session:
                    await session.close()

        try:
            return run_async(_set_volume_async(), timeout=5.0)
        except Exception as e:
            log.error(f"[MiDevice] Set volume error: {e}")
            return -1, -1

    def get_device_did(self) -> tuple[int, str]:
        """
        获取设备did
        :return: (错误码, did)
        """
        try:
            if self.device_did is None:
                code, self.device_did = run_async(_get_device_did_async(self.username, self.password, self.device_id),
                                                  timeout=5.0)
                if code != 0:
                    return code, "设备未找到"
            return 0, self.device_did
        except Exception as e:
            log.error(f"[MiDevice] Get device did error: {e}")
            return -1, "设备未找到"


# 同步包装函数（用于在Flask路由中使用）


def scan_devices_sync(timeout: float = 5.0) -> List[Dict]:
    """同步扫描设备"""
    try:
        username = os.getenv("MI_USER", DEFAULT_MI_USERNAME)
        password = os.getenv("MI_PASS", DEFAULT_MI_PASSWORD)
        return run_async(MiDevice.scan_devices(username, password), timeout=timeout + 2.0)
    except asyncio.TimeoutError:
        log.error(f"[MiDevice] Scan timeout after {timeout + 2.0}s")
        return []
    except Exception as e:
        log.error(f"[MiDevice] Scan error: {e}")
        return []
