'''
小米设备管理
'''
import asyncio
import os
from pathlib import Path
from turtle import st
from typing import Any, Dict, List, Optional

from aiohttp import ClientSession
from miservice import MiAccount, MiNAService

from core.utils import run_async, convert_to_http_url
from core.log_config import root_logger

log = root_logger()

# 默认的小米账号信息（可以从配置中读取）
DEFAULT_MI_USERNAME = "adanzl@163.com"
DEFAULT_MI_PASSWORD = "Zhao575936"


def _device_to_dict(device) -> Dict:
    """将 Device 对象转换为字典"""
    try:
        print(type(device))
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


class MiDevice:
    """小米设备管理"""
    scanning = False

    def __init__(self, address: str, name: str = "", username: str = None, password: str = None):
        """
        初始化小米设备
        :param address: 设备ID或地址
        :param name: 设备名称
        :param username: 小米账号用户名（可选，使用默认值）
        :param password: 小米账号密码（可选，使用默认值）
        """
        self.device_id = address  # 小米设备使用 deviceID 作为地址
        self.name = name or address
        self.username = username or DEFAULT_MI_USERNAME
        self.password = password or DEFAULT_MI_PASSWORD
        self._mina_service = None

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

    def _get_mina_service(self) -> MiNAService:
        """获取 MiNAService 对象"""
        if self._mina_service is None:
            with ClientSession() as session:
                account = MiAccount(
                    session,
                    self.username,
                    self.password,
                    os.path.join(str(Path.home()), ".mi.token"),
                )
                self._mina_service = MiNAService(account)
        return self._mina_service

    # ========== 统一设备接口 ==========
    def play(self, url: str) -> tuple[int, str]:
        """
        播放媒体文件【OUT】
        :param url: 媒体文件 URL (可以是 http://、file:// 或本地文件路径)
        :return: (错误码, 消息)
        """
        try:
            media_url = convert_to_http_url(url)
            mina_service = self._get_mina_service()
            mina_service.play_by_url(self.device_id, media_url)
            return 0, "ok"
        except Exception as e:
            log.error(f"[MiDevice] Play error: {e}")
            return -1, f"播放失败: {str(e)}"

    def stop(self) -> tuple[int, str]:
        """
        停止播放【OUT】
        :return: (错误码, 消息)
        """
        try:
            mina_service = self._get_mina_service()
            mina_service.player_stop(self.device_id)
            return 0, "ok"
        except Exception as e:
            log.error(f"[MiDevice] Stop error: {e}")
            return -1, f"停止失败: {str(e)}"

    def get_position_info(self) -> tuple[int, dict]:
        """
        获取播放位置信息【OUT】
        :return: (错误码, 位置信息)
        """
        return 0, {"position": 0, "duration": 0}

    def get_transport_info(self) -> tuple[int, dict]:
        """
        获取播放传输信息【OUT】
        :return: (错误码, 传输信息)
        """
        return 0, {"transport_info": "ok"}

# 同步包装函数（用于在Flask路由中使用）


def scan_devices_sync(timeout: float = 5.0) -> List[Dict]:
    """同步扫描设备"""
    try:
        return run_async(MiDevice.scan_devices("adanzl@163.com", "Zhao575936"), timeout=timeout + 2.0)
    except asyncio.TimeoutError:
        log.error(f"[MiDevice] Scan timeout after {timeout + 2.0}s")
        return []
    except Exception as e:
        log.error(f"[MiDevice] Scan error: {e}")
        return []
