'''
小米设备管理
'''
# 必须在导入 miservice 之前 patch fake_useragent，避免 ThreadPoolExecutor 导致的 LoopExit
from core.device.base import DeviceBase
from core.tools.useragent_fix import patch_fake_useragent

patch_fake_useragent()

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from aiohttp import ClientSession
from miservice import MiAccount, MiNAService

from core.config import app_logger, config
from core.tools.async_util import run_async
from core.utils import convert_to_http_url, format_time_str

log = app_logger

# 从环境变量读取小米账号信息，如果没有则使用默认值
DEFAULT_MI_USERNAME = config.MI_USER
DEFAULT_MI_PASSWORD = config.MI_PASS

# Token 文件路径
TOKEN_FILE = os.path.join(str(Path.home()), ".mi.token")


def _device_to_dict(device: Dict[str, Any]) -> Dict[str, str]:
    """将 Device 对象转换为字典"""
    try:
        return {
            "address": device.get('address', ''),
            "name": device.get('name', ''),
            "deviceID": device.get('deviceID', ''),
            "presence": device.get('presence', 'offline'),
            "miotDID": device.get('miotDID', ''),
            "mac": device.get('mac', ''),
        }
    except Exception as e:
        log.error(f"[MiDevice] Error converting device: {e}")
        return {}


async def _get_device_did_async(username: str, password: str, device_id: str) -> Tuple[int, str]:
    session = None
    try:
        session = ClientSession()
        account = MiAccount(session, username, password, TOKEN_FILE)
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


class MiDevice(DeviceBase):
    """小米设备管理"""
    scanning = False

    def __init__(self,
                 address: str,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 name: str = "") -> None:
        """初始化小米设备。

        Args:
            address (str): 设备 ID。
            username (Optional[str]): 小米账号用户名。如果为 None，则从配置中读取。
            password (Optional[str]): 小米账号密码。如果为 None，则从配置中读取。
            name (str): 设备名称。
        """
        super().__init__(name=name)
        self.device_id = address  # 小米设备使用 deviceID 作为地址
        self.username = username or DEFAULT_MI_USERNAME
        self.password = password or DEFAULT_MI_PASSWORD
        self.device_did = None

    @staticmethod
    async def scan_devices(username: Optional[str] = None, password: Optional[str] = None) -> List[Dict[str, str]]:
        """扫描小米设备

        Args:
            username (Optional[str]): 小米账号用户名（可选，使用默认值）
            password (Optional[str]): 小米账号密码（可选，使用默认值）

        Returns:
            List[Dict[str, str]]: 设备列表
        """
        if MiDevice.scanning:
            log.warning("[MiDevice] Already scanning")
            return []

        username = username or DEFAULT_MI_USERNAME
        password = password or DEFAULT_MI_PASSWORD

        # 验证账号密码是否设置
        if not username or not password:
            error_msg = "小米账号或密码未设置，请设置环境变量 MI_USER 和 MI_PASS"
            log.error(f"[MiDevice] {error_msg}")
            return []

        try:
            MiDevice.scanning = True
            log.info(f"[MiDevice] Starting scan with username: {username[:3]}***")
            async with ClientSession() as session:
                account = MiAccount(
                    session,
                    username,
                    password,
                    TOKEN_FILE,
                )
                mina_service = MiNAService(account)
                result = await mina_service.device_list()
                # log.info(f"[MiDevice] Device list: {result}")
                device_list = [_device_to_dict(device) for device in result]
                log.info(f"[MiDevice] Found {len(device_list)} devices")
            return device_list

        except Exception as e:
            # 捕获 gevent LoopExit 异常（可能由 fake_useragent 的线程池操作引起）
            import gevent
            if isinstance(e, gevent.exceptions.LoopExit):
                log.warning(f"[MiDevice] Scan: gevent LoopExit (可忽略)")
                return []

            # 检查是否是登录失败
            error_str = str(e)
            if "Login failed" in error_str or "登录验证失败" in error_str or "70016" in error_str:
                log.error(f"[MiDevice] 登录验证失败，请检查账号密码是否正确。错误: {e}")
            else:
                log.error(f"[MiDevice] Scan error: {e}")
            return []
        finally:
            MiDevice.scanning = False

    def _create_account(self, session: ClientSession) -> MiAccount:
        return MiAccount(session, self.username, self.password, TOKEN_FILE)

    # ========== 统一设备接口 ==========
    def play(self, url: str) -> Tuple[int, str]:
        """在小米设备上播放指定的媒体 URL。

        Args:
            url (str): 媒体文件的 URL，会自动转换为 HTTP URL。

        Returns:
            Tuple[int, str]: (code, msg)。code=0 表示成功。
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
                return 0, "ok"
            except Exception as e:
                # 捕获 gevent LoopExit 异常（可能由 fake_useragent 的线程池操作引起）
                import gevent
                if isinstance(e, gevent.exceptions.LoopExit):
                    log.warning(f"[MiDevice] Play: gevent LoopExit (可忽略), 重试播放")
                    # 重试一次
                    try:
                        await mina_service.play_by_url(self.device_id, media_url)
                        return 0, "ok"
                    except Exception as e2:
                        log.error(f"[MiDevice] Play retry error: {e2}")
                        return -1, f"播放失败: {str(e2)}"

                error_str = str(e)
                if "Login failed" in error_str or "登录验证失败" in error_str or "70016" in error_str:
                    log.error(f"[MiDevice] 登录验证失败，请检查账号密码是否正确: {e}")
                    return -1, "登录验证失败，请检查账号密码是否正确"

                log.error(f"[MiDevice] Play error: {e}")
                return -1, f"播放失败: {str(e)}"
            finally:
                if session:
                    await session.close()

        try:
            return run_async(_play_async(), timeout=20.0)
        except Exception as e:
            # 捕获 gevent LoopExit 异常
            import gevent
            if isinstance(e, gevent.exceptions.LoopExit):
                log.warning(f"[MiDevice] Play: gevent LoopExit (可忽略)")
                return -1, "播放失败: gevent LoopExit"
            log.error(f"[MiDevice] Play error: {e}")
            return -1, f"播放失败: {str(e)}"

    def stop(self) -> Tuple[int, str]:
        """停止小米设备上的播放。

        Returns:
            Tuple[int, str]: (code, msg)。code=0 表示成功。
        """

        async def _stop_async():
            session = None
            try:
                # 获取 MiNAService 对象
                session = ClientSession()
                account = self._create_account(session)
                mina_service = MiNAService(account)
                await mina_service.player_pause(self.device_id)
                await mina_service.player_stop(self.device_id)
                return 0, "ok"
            except Exception as e:
                error_str = str(e)
                if "Login failed" in error_str or "登录验证失败" in error_str or "70016" in error_str:
                    log.error(f"[MiDevice] 登录验证失败，请检查账号密码是否正确: {e}")
                    return -1, "登录验证失败，请检查账号密码是否正确"
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

    def get_status(self) -> Tuple[int, Dict[str, Any]]:
        """获取小米设备的播放状态。

        Returns:
            Tuple[int, Dict[str, Any]]: (code, status_dict)。code=0 表示成功。
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
                state = 'STOPPED' if info.get('status') == 2 else 'PLAYING'
                state_code = info.get('status')
                volume = info.get('volume', 0)  # 获取音量，确保始终有音量值

                # 安全访问 play_song_detail，如果不存在或为空则返回基本状态（包含音量）
                play_song_detail = info.get('play_song_detail')
                if not play_song_detail or not isinstance(play_song_detail, dict) or len(play_song_detail) == 0:
                    # 如果没有播放详情，返回基本状态（确保包含音量）
                    return 0, {
                        "state": state,
                        "state_code": state_code,
                        "status": 'OK',
                        "track": 0,
                        "duration": "00:00:00",
                        "position": "00:00:00",
                        "volume": volume  # 确保音量始终返回
                    }

                duration = format_time_str(play_song_detail['duration'] /
                                           1000) if play_song_detail.get('duration') else '00:00:00'
                track_list = info.get('track_list', [])
                audio_id = play_song_detail.get('audio_id')
                position = play_song_detail.get('position', 0)  # 播放位置 单位：毫秒

                track = 0
                if audio_id and track_list:
                    try:
                        track = track_list.index(audio_id) + 1
                    except ValueError:
                        track = 0

                return 0, {
                    "state": state,  # PLAYING, STOPPED
                    "state_code": state_code,
                    "status": 'OK',  # OK, ERROR
                    "track": track,  # 当前曲目索引（从1开始）
                    "duration": duration,  # 总时长，格式如 "00:03:45"
                    "position": format_time_str(position / 1000),  # 已播放时长，格式如 "00:01:30"
                    "volume": volume  # 音量
                }
            except Exception as e:
                error_str = str(e)
                if "Login failed" in error_str or "登录验证失败" in error_str or "70016" in error_str:
                    log.error(f"[MiDevice] 登录验证失败，请检查账号密码是否正确: {e}")
                    return -1, {"error": "登录验证失败，请检查账号密码是否正确"}
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
    def get_volume(self) -> Tuple[int, int]:
        """获取小米设备的音量。

        Returns:
            Tuple[int, int]: (code, volume)。code=0 表示成功。
        """
        # 复用 get_status 方法，避免重复代码
        code, status = self.get_status()
        if code != 0:
            return code, 0

        # 从状态字典中提取音量，如果不存在则返回 0
        volume = status.get('volume', 0)
        return 0, volume

    def set_volume(self, volume: int) -> Tuple[int, str]:
        """设置小米设备的音量。

        Args:
            volume (int): 目标音量。

        Returns:
            Tuple[int, str]: (code, msg)。code=0 表示成功。
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
                error_str = str(e)
                if "Login failed" in error_str or "登录验证失败" in error_str or "70016" in error_str:
                    log.error(f"[MiDevice] 登录验证失败，请检查账号密码是否正确: {e}")
                    return -1, "登录验证失败，请检查账号密码是否正确"
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

    def get_device_did(self) -> Tuple[int, str]:
        """获取小米设备的设备ID。

        Returns:
            Tuple[int, str]: (code, did)。code=0 表示成功。
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


def scan_devices_sync(timeout: float = 5.0) -> List[Dict[str, str]]:
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
