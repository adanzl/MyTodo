'''
VLC 播放器封装（支持多设备）
'''
import vlc
import time
import os
from typing import Dict, Optional, Any
from core.log_config import root_logger

log = root_logger()


class VLCPlayer:
    """VLC 播放器（单个设备）"""

    def __init__(self, alsa_device: str, hci_adapter: str = 'hci0'):
        """
        初始化 VLC 播放器
        :param alsa_device: ALSA 设备名称，例如 "bluealsa:HCI=hci0,DEV=XX:XX:XX:XX:XX:XX,PROFILE=a2dp"
        :param hci_adapter: HCI 适配器名称（用于日志）
        """
        # 验证必须是 bluealsa 格式
        if not alsa_device.startswith('bluealsa:'):
            raise ValueError(f"ALSA device must be bluealsa format, got: {alsa_device}")
        
        self.alsa_device = alsa_device
        self.hci_adapter = hci_adapter
        self.instance = None
        self.media_player = None
        self.current_media = None
        self.current_file = None
        self._init_vlc()

    def _init_vlc(self):
        """初始化 VLC 实例"""
        try:
            # 创建 VLC 实例，指定 ALSA 设备
            instance_args = [
                '--aout=alsa',
                f'--alsa-audio-device={self.alsa_device}',
                '--intf', 'dummy',  # 无界面模式
                '--quiet',  # 减少输出
            ]
            self.instance = vlc.Instance(instance_args)
            self.media_player = self.instance.media_player_new()
            log.info(f"[VLC] Initialized player for device: {self.alsa_device}")
        except Exception as e:
            log.error(f"[VLC] Failed to initialize VLC: {e}")
            raise

    def play(self, file_path: str, position: float = 0.0) -> Dict[str, Any]:
        """
        播放文件
        :param file_path: 文件路径
        :param position: 起始位置（秒），0.0 表示从头开始
        :return: 播放结果
        """
        try:
            if not os.path.exists(file_path):
                return {"code": -1, "msg": f"File not found: {file_path}"}

            # 创建媒体对象
            media = self.instance.media_new(file_path)
            self.media_player.set_media(media)
            self.current_media = media
            self.current_file = file_path

            # 如果指定了起始位置，设置位置
            if position > 0:
                # 等待媒体加载后设置位置
                self.media_player.play()
                time.sleep(0.1)  # 等待媒体加载
                duration = self.media_player.get_length()
                if duration > 0:
                    pos = position / (duration / 1000.0)  # 转换为 0.0-1.0
                    self.media_player.set_position(pos)

            # 播放
            result = self.media_player.play()
            if result == 0:
                log.info(f"[VLC] Playing: {file_path} on {self.alsa_device}")
                return {"code": 0, "msg": "Playing", "data": {"file": os.path.basename(file_path)}}
            else:
                return {"code": -1, "msg": "Failed to start playback"}
        except Exception as e:
            log.error(f"[VLC] Play error: {e}")
            return {"code": -1, "msg": f"Play failed: {str(e)}"}

    def pause(self) -> Dict[str, Any]:
        """暂停播放"""
        try:
            state = self.media_player.get_state()
            if state == vlc.State.Playing:
                self.media_player.pause()
                return {"code": 0, "msg": "Paused"}
            elif state == vlc.State.Paused:
                return {"code": 0, "msg": "Already paused"}
            else:
                return {"code": -1, "msg": "Not playing"}
        except Exception as e:
            log.error(f"[VLC] Pause error: {e}")
            return {"code": -1, "msg": f"Pause failed: {str(e)}"}

    def resume(self) -> Dict[str, Any]:
        """恢复播放"""
        try:
            state = self.media_player.get_state()
            if state == vlc.State.Paused:
                self.media_player.play()
                return {"code": 0, "msg": "Resumed"}
            elif state == vlc.State.Playing:
                return {"code": 0, "msg": "Already playing"}
            else:
                return {"code": -1, "msg": "Not paused"}
        except Exception as e:
            log.error(f"[VLC] Resume error: {e}")
            return {"code": -1, "msg": f"Resume failed: {str(e)}"}

    def stop(self) -> Dict[str, Any]:
        """停止播放"""
        try:
            self.media_player.stop()
            self.current_media = None
            self.current_file = None
            return {"code": 0, "msg": "Stopped"}
        except Exception as e:
            log.error(f"[VLC] Stop error: {e}")
            return {"code": -1, "msg": f"Stop failed: {str(e)}"}

    def seek(self, position: float) -> Dict[str, Any]:
        """
        跳转到指定位置
        :param position: 位置（秒）或比例（0.0-1.0）
        :return: 跳转结果
        """
        try:
            duration = self.media_player.get_length()  # 毫秒
            
            if duration <= 0:
                return {"code": -1, "msg": "No media loaded"}

            # 如果 position > 1.0，认为是秒数，否则认为是比例
            if position > 1.0:
                pos = position / (duration / 1000.0)
            else:
                pos = position

            if 0.0 <= pos <= 1.0:
                self.media_player.set_position(pos)
                return {"code": 0, "msg": "Seeked", "data": {"position": pos * duration / 1000.0}}
            else:
                return {"code": -1, "msg": "Invalid position"}
        except Exception as e:
            log.error(f"[VLC] Seek error: {e}")
            return {"code": -1, "msg": f"Seek failed: {str(e)}"}

    def get_status(self) -> Dict[str, Any]:
        """获取播放状态"""
        try:
            state = self.media_player.get_state()
            state_map = {
                vlc.State.Playing: 'playing',
                vlc.State.Paused: 'paused',
                vlc.State.Stopped: 'stopped',
                vlc.State.Ended: 'ended',
                vlc.State.Error: 'error',
                vlc.State.NothingSpecial: 'idle',
                vlc.State.Opening: 'opening',
                vlc.State.Buffering: 'buffering',
            }

            position = self.media_player.get_position()  # 0.0-1.0
            time_ms = self.media_player.get_time()  # 毫秒
            length_ms = self.media_player.get_length()  # 毫秒

            status_data = {
                "state": state_map.get(state, 'unknown'),
                "position": position,  # 0.0-1.0
                "time": time_ms / 1000.0 if time_ms > 0 else 0.0,  # 秒
                "duration": length_ms / 1000.0 if length_ms > 0 else 0.0,  # 秒
                "volume": self.media_player.audio_get_volume(),
                "file": os.path.basename(self.current_file) if self.current_file else None,
                "alsa_device": self.alsa_device,
            }

            return {
                "code": 0,
                "data": status_data,
                "msg": "ok"
            }
        except Exception as e:
            log.error(f"[VLC] Get status error: {e}")
            return {"code": -1, "msg": f"Get status failed: {str(e)}"}

    def set_volume(self, volume: int) -> Dict[str, Any]:
        """
        设置音量
        :param volume: 音量 0-100
        :return: 设置结果
        """
        try:
            volume = max(0, min(100, volume))  # 限制在 0-100
            result = self.media_player.audio_set_volume(volume)
            if result == 0:
                return {"code": 0, "msg": "Volume set", "data": {"volume": volume}}
            else:
                return {"code": -1, "msg": "Failed to set volume"}
        except Exception as e:
            log.error(f"[VLC] Set volume error: {e}")
            return {"code": -1, "msg": f"Set volume failed: {str(e)}"}

    def release(self):
        """释放资源"""
        try:
            if self.media_player:
                self.media_player.stop()
                self.media_player.release()
            if self.instance:
                self.instance.release()
            log.info(f"[VLC] Released player for device: {self.alsa_device}")
        except Exception as e:
            log.error(f"[VLC] Release error: {e}")

