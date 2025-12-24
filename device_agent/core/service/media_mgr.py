'''
媒体管理服务（使用 VLC + bluealsa）
'''
import os
import time
from typing import Dict, Optional, Any, List
from core.log_config import root_logger
from core.config import config_mgr
from core.utils import _ok, _err
from core.service.bluetooth_mgr import bluetooth_mgr
from core.service.vlc_player import VLCPlayer

log = root_logger()


class MediaMgr:
    """媒体管理器（支持多设备播放）"""

    def __init__(self):
        log.info("[MEDIA] MediaMgr init (VLC + bluealsa)")
        # 存储每个设备的播放器实例：device_address -> VLCPlayer
        self._players: Dict[str, VLCPlayer] = {}


    def get_status(self, device_address: Optional[str] = None) -> Dict[str, Any]:
        """
        获取播放状态
        :param device_address: 设备地址（可选，如果不指定则返回所有设备状态）
        :return: 播放状态字典
        """
        try:
            if device_address:
                # 返回指定设备的状态
                device_address_upper = device_address.upper()
                if device_address_upper in self._players:
                    player = self._players[device_address_upper]
                    return player.get_status()
                else:
                    return {"code": -1, "msg": "Device not playing"}
            else:
                # 返回所有设备的状态
                all_status = {}
                for addr, player in self._players.items():
                    status_result = player.get_status()
                    # player.get_status() 返回 {"code": 0, "data": {...}, "msg": "ok"}
                    if status_result.get("code") == 0:
                        all_status[addr] = status_result.get("data", {})
                    else:
                        all_status[addr] = status_result
                return {"code": 0, "data": all_status}
        except Exception as e:
            log.error(f"[MEDIA] Error getting status: {e}")
            return {"code": -1, "msg": f"Get status failed: {str(e)}"}

    def stop(self, device_address: Optional[str] = None) -> Dict[str, Any]:
        """
        停止播放
        :param device_address: 设备地址（可选，如果不指定则停止所有设备）
        :return: 停止结果
        """
        try:
            if device_address:
                # 停止指定设备
                device_address_upper = device_address.upper()
                if device_address_upper in self._players:
                    player = self._players[device_address_upper]
                    result = player.stop()
                    # 不删除播放器实例，保留以便后续使用
                    return result
                else:
                    return {"code": 0, "msg": "Device not playing"}
            else:
                # 停止所有设备
                stopped_count = 0
                for addr, player in self._players.items():
                    try:
                        player.stop()
                        stopped_count += 1
                    except Exception as e:
                        log.error(f"[MEDIA] Error stopping device {addr}: {e}")
                return {"code": 0, "msg": f"Stopped {stopped_count} device(s)"}
        except Exception as e:
            log.error(f"[MEDIA] Stop error: {e}")
            return {"code": -1, "msg": f"Stop failed: {str(e)}"}

    def pause(self, device_address: str) -> Dict[str, Any]:
        """
        暂停播放
        :param device_address: 设备地址
        :return: 暂停结果
        """
        try:
            device_address_upper = device_address.upper()
            if device_address_upper in self._players:
                player = self._players[device_address_upper]
                return player.pause()
            else:
                return {"code": -1, "msg": "Device not playing"}
        except Exception as e:
            log.error(f"[MEDIA] Pause error: {e}")
            return {"code": -1, "msg": f"Pause failed: {str(e)}"}

    def resume(self, device_address: str) -> Dict[str, Any]:
        """
        恢复播放
        :param device_address: 设备地址
        :return: 恢复结果
        """
        try:
            device_address_upper = device_address.upper()
            if device_address_upper in self._players:
                player = self._players[device_address_upper]
                return player.resume()
            else:
                return {"code": -1, "msg": "Device not playing"}
        except Exception as e:
            log.error(f"[MEDIA] Resume error: {e}")
            return {"code": -1, "msg": f"Resume failed: {str(e)}"}

    def seek(self, device_address: str, position: float) -> Dict[str, Any]:
        """
        跳转播放位置
        :param device_address: 设备地址
        :param position: 位置（秒）或比例（0.0-1.0）
        :return: 跳转结果
        """
        try:
            device_address_upper = device_address.upper()
            if device_address_upper in self._players:
                player = self._players[device_address_upper]
                return player.seek(position)
            else:
                return {"code": -1, "msg": "Device not playing"}
        except Exception as e:
            log.error(f"[MEDIA] Seek error: {e}")
            return {"code": -1, "msg": f"Seek failed: {str(e)}"}

    def set_volume(self, device_address: str, volume: int) -> Dict[str, Any]:
        """
        设置音量
        :param device_address: 设备地址
        :param volume: 音量 0-100
        :return: 设置结果
        """
        try:
            device_address_upper = device_address.upper()
            if device_address_upper in self._players:
                player = self._players[device_address_upper]
                return player.set_volume(volume)
            else:
                return {"code": -1, "msg": "Device not playing"}
        except Exception as e:
            log.error(f"[MEDIA] Set volume error: {e}")
            return {"code": -1, "msg": f"Set volume failed: {str(e)}"}

    def _get_or_create_player(self, device_address: str, alsa_device: str, hci_adapter: str = 'hci0') -> VLCPlayer:
        """
        获取或创建播放器实例
        :param device_address: 设备地址
        :param alsa_device: ALSA 设备名称
        :param hci_adapter: HCI 适配器名称
        :return: VLCPlayer 实例
        """
        device_address_upper = device_address.upper()
        
        if device_address_upper not in self._players:
            # 创建新的播放器实例
            player = VLCPlayer(alsa_device, hci_adapter)
            self._players[device_address_upper] = player
            log.info(f"[MEDIA] Created new player for device: {device_address_upper}")
        else:
            # 使用现有播放器
            player = self._players[device_address_upper]
            # 如果 ALSA 设备改变了，需要重新创建
            if player.alsa_device != alsa_device:
                log.info(f"[MEDIA] ALSA device changed, recreating player for {device_address_upper}")
                player.release()
                player = VLCPlayer(alsa_device, hci_adapter)
                self._players[device_address_upper] = player
        
        return player

    def _resolve_alsa_device(self, device_address: Optional[str], alsa_device: Optional[str], hci_adapter: str = 'hci0') -> Optional[str]:
        """
        解析 ALSA 设备
        :param device_address: 蓝牙设备地址
        :param alsa_device: 直接指定的 ALSA 设备
        :param hci_adapter: HCI 适配器名称
        :return: ALSA 设备名称
        """
        # 如果直接指定了 ALSA 设备，直接返回
        if alsa_device:
            return alsa_device
        
        # 如果提供了设备地址，直接构造 ALSA 设备名，不需要查询配对设备列表
        if device_address:
            alsa_device = f"bluealsa:HCI={hci_adapter},DEV={device_address.upper()},PROFILE=a2dp"
            log.info(f"[MEDIA] Using ALSA device: {alsa_device}")
            return alsa_device
        
        # 没有指定任何设备，尝试获取第一个蓝牙设备
        alsa_device = bluetooth_mgr.get_alsa_name(None, hci_adapter)
        if alsa_device:
            log.info(f"[MEDIA] Using default ALSA device: {alsa_device}")
        return alsa_device

    def _connect_bluetooth_if_needed(self, device_address: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        如果需要，连接蓝牙设备
        :param device_address: 设备地址
        :return: 设备信息字典，如果连接失败或未提供地址则返回 None
        """
        if not device_address:
            return None

        # 先检查设备是否已连接，避免不必要的连接操作
        if bluetooth_mgr._check_device_connected(device_address):
            # 设备已连接，获取设备信息
            device_info_result = bluetooth_mgr.get_info(device_address)
            if device_info_result.get('code') == 0:
                return device_info_result.get('data', {})
            # 如果获取信息失败，继续尝试连接

        connect_result = bluetooth_mgr.connect_device_sync(device_address, timeout=10.0)
        if connect_result.get('code') == 0:
            log.info(f"[MEDIA] Connected to bluetooth device: {device_address}")
            return connect_result.get('data', {})
        else:
            log.warning(f"[MEDIA] Failed to connect: {connect_result.get('msg')}")
            return None

    def play(self, file_path: str, device_address: Optional[str] = None, 
             alsa_device: Optional[str] = None, hci_adapter: str = 'hci0',
             position: float = 0.0) -> Dict[str, Any]:
        """
        播放媒体文件（完整流程）
        :param file_path: 文件路径
        :param device_address: 蓝牙设备地址（可选）
        :param alsa_device: 直接指定的 ALSA 设备（可选）
        :param hci_adapter: HCI 适配器名称，默认为 hci0
        :param position: 起始位置（秒），0.0 表示从头开始
        :return: 播放结果字典
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return {"code": -1, "msg": f"File not found: {file_path}"}

            # 如果没有指定设备地址，尝试使用默认设备
            if not device_address:
                device_address = config_mgr.get_default_bluetooth_device()
                if device_address:
                    log.info(f"[MEDIA] Using default bluetooth device: {device_address}")

            if not device_address and not alsa_device:
                return {"code": -1, "msg": "No device specified"}

            # 连接蓝牙设备（如果需要）
            bluetooth_device = self._connect_bluetooth_if_needed(device_address)

            # 解析 ALSA 设备
            alsa_device = self._resolve_alsa_device(device_address, alsa_device, hci_adapter)
            if not alsa_device:
                return {"code": -1, "msg": "Failed to resolve ALSA device"}

            # 获取或创建播放器实例
            if device_address:
                player = self._get_or_create_player(device_address, alsa_device, hci_adapter)
            else:
                # 如果没有设备地址，使用 ALSA 设备名作为标识
                device_key = alsa_device
                if device_key not in self._players:
                    player = VLCPlayer(alsa_device, hci_adapter)
                    self._players[device_key] = player
                else:
                    player = self._players[device_key]

            # 播放文件
            result = player.play(file_path, position)
            
            if result.get('code') == 0:
                data = result.get('data', {})
                if isinstance(data, dict):
                    data.update({
                        "alsa_device": alsa_device,
                        "bluetooth_device": bluetooth_device,
                        "hci_adapter": hci_adapter,
                        "device_address": device_address
                    })
                return {
                    "code": 0,
                    "msg": result.get('msg', 'Playing'),
                    "data": data
                }
            else:
                return result

        except Exception as e:
            log.error(f"[MEDIA] Play error: {e}")
            return {"code": -1, "msg": f"Play failed: {str(e)}"}


# 全局实例
media_mgr = MediaMgr()

