'''
媒体管理服务
'''
import os
import time
from typing import Dict, Optional, Any, List
from gevent import subprocess
from core.log_config import root_logger
from core.config import config_mgr
from core.utils import _ok, _err
from core.service.bluetooth_mgr import bluetooth_mgr

log = root_logger()


class MediaMgr:
    """媒体管理器"""

    def __init__(self):
        log.info("[MEDIA] MediaMgr init")
        self._current_playback_process = None


    def get_status(self) -> Dict[str, Any]:
        """
        获取当前播放状态
        :return: 播放状态字典 {"is_playing": bool, "pid": int or None}
        """
        try:
            if self._current_playback_process and self._current_playback_process.poll() is None:
                # 进程还在运行
                return {"is_playing": True, "pid": self._current_playback_process.pid}
            else:
                return {"is_playing": False, "pid": None}
        except Exception as e:
            log.error(f"[MEDIA] Error checking playback status: {e}")
            return {"is_playing": False, "pid": None}

    def _terminate_process(self, process: subprocess.Popen) -> None:
        """
        终止进程（优雅终止，必要时强制杀死）
        :param process: 要终止的进程
        """
        log.info(f"[MEDIA] Terminating playback process (PID: {process.pid})")
        process.terminate()
        try:
            process.wait(timeout=2)
            log.info(f"[MEDIA] Process {process.pid} terminated gracefully")
        except subprocess.TimeoutExpired:
            log.warning(f"[MEDIA] Process {process.pid} did not terminate, killing it")
            process.kill()
            process.wait()
            log.info(f"[MEDIA] Process {process.pid} killed")

    def stop(self) -> Any:
        """
        停止当前正在播放的音频
        :return: 停止结果
        """
        log.debug(f"[MEDIA] stop_current_playback called, _current_playback_process={self._current_playback_process}")

        if self._current_playback_process is None:
            log.info("[MEDIA] No playback process reference")
            return _ok(msg="No playback in progress (no process reference)")

        poll_result = self._current_playback_process.poll()
        log.debug(f"[MEDIA] Process poll result: {poll_result}, PID: {self._current_playback_process.pid}")

        if poll_result is None:
            # 进程还在运行，需要终止
            self._terminate_process(self._current_playback_process)
            self._current_playback_process = None
            return _ok(msg="Playback stopped")
        else:
            # 进程已经结束
            log.info(f"[MEDIA] Process (PID: {self._current_playback_process.pid}) already exited with code {poll_result}")
            self._current_playback_process = None
            return _ok(msg=f"No playback in progress (process already exited with code {poll_result})")

    def _prepare_audio_env(self) -> Dict[str, str]:
        """
        准备音频播放所需的环境变量
        :return: 环境变量字典
        """
        env = os.environ.copy()
        try:
            if 'XDG_RUNTIME_DIR' not in env:
                env['XDG_RUNTIME_DIR'] = f"/run/user/{os.getuid()}"
            if 'HOME' not in env:
                env['HOME'] = os.path.expanduser('~')
        except Exception:
            pass
        return env

    def _build_mpg123_command(self, file_path: str, alsa_device: Optional[str] = None) -> List[str]:
        """
        构建 mpg123 命令
        :param file_path: 文件路径
        :param alsa_device: ALSA 设备名称（可选）
        :return: 命令列表
        """
        cmd = ['mpg123']
        if alsa_device:
            cmd.extend(['-a', alsa_device])
        cmd.append(file_path)
        return cmd

    def _play_with_mpg123(self, file_path: str, alsa_device: Optional[str] = None) -> Any:
        """
        使用 mpg123 播放音频文件
        :param file_path: 文件路径
        :param alsa_device: ALSA 设备名称（例如 "bluealsa:HCI=hci0,DEV=XX:XX:XX:XX:XX:XX,PROFILE=a2dp"）
        :return: 播放结果
        """
        try:
            cmd = self._build_mpg123_command(file_path, alsa_device)
            log.info(f"[MEDIA]: {' '.join(cmd)}")

            # 启动播放进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self._prepare_audio_env(),
                start_new_session=True
            )

            self._current_playback_process = process
            log.info(f"[MEDIA] Started playback: {file_path} (PID: {process.pid})")

            # 检查进程是否立即退出（可能是错误）
            time.sleep(0.1)
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                log.error(f"[MEDIA] mpg123 exited immediately. stderr: {stderr}")
                return _err(msg=f"mpg123 failed: {stderr}")

            return _ok(data={"file": os.path.basename(file_path), "pid": process.pid}, msg="Playing")

        except FileNotFoundError:
            log.error("[MEDIA] mpg123 not found")
            return _err(msg="mpg123 not installed")
        except Exception as e:
            log.error(f"[MEDIA] Error playing file: {e}")
            return _err(msg=f"Play failed: {str(e)}")

    def _resolve_alsa_device(self, device_address: Optional[str], alsa_device: Optional[str]) -> Optional[str]:
        """
        解析 ALSA 设备
        :param device_address: 蓝牙设备地址
        :param alsa_device: 直接指定的 ALSA 设备
        :return: ALSA 设备名称
        """
        if alsa_device:
            return alsa_device
        
        if device_address:
            alsa_device = bluetooth_mgr.get_alsa_name(device_address)
            if alsa_device:
                log.info(f"[MEDIA] Found ALSA device: {alsa_device}")
                return alsa_device
        
        # 没有指定任何设备，尝试获取第一个蓝牙设备
        alsa_device = bluetooth_mgr.get_alsa_name()
        if alsa_device:
            log.info(f"[MEDIA] Using default ALSA device: {alsa_device}")
        return alsa_device

    def _extract_result_data(self, result: Any) -> Optional[Dict[str, Any]]:
        """
        从响应对象或字典中提取数据
        :param result: 响应对象或字典
        :return: 结果字典
        """
        if hasattr(result, 'get_json'):
            return result.get_json()
        elif isinstance(result, dict):
            return result
        return None

    def _connect_bluetooth_if_needed(self, device_address: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        如果需要，连接蓝牙设备
        :param device_address: 设备地址
        :return: 设备信息字典，如果连接失败或未提供地址则返回 None
        """
        if not device_address:
            return None

        connect_result = bluetooth_mgr.connect_device_sync(device_address, timeout=10.0)
        if connect_result.get('code') == 0:
            log.info(f"[MEDIA] Connected to bluetooth device: {device_address}")
            return connect_result.get('data', {})
        else:
            log.warning(f"[MEDIA] Failed to connect: {connect_result.get('msg')}")
            return None

    def play(self, file_path: str, device_address: Optional[str] = None, alsa_device: Optional[str] = None) -> Dict[str, Any]:
        """
        播放媒体文件（完整流程）
        :param file_path: 文件路径
        :param device_address: 蓝牙设备地址（可选）
        :param alsa_device: 直接指定的 ALSA 设备（可选）
        :return: 播放结果字典
        """
        # 如果没有指定设备地址，尝试使用默认设备
        if not device_address:
            device_address = config_mgr.get_default_bluetooth_device()
            if device_address:
                log.info(f"[MEDIA] 使用默认蓝牙设备: {device_address}")

        # 停止当前播放
        self.stop()

        # 连接蓝牙设备（如果需要）
        bluetooth_device = self._connect_bluetooth_if_needed(device_address)

        # 解析 ALSA 设备
        alsa_device = self._resolve_alsa_device(device_address, alsa_device)

        # 播放文件
        result = self._play_with_mpg123(file_path, alsa_device)
        result_data = self._extract_result_data(result)

        # 处理成功响应，添加额外信息
        if result_data and result_data.get('code') == 0:
            data = result_data.get('data', {})
            if isinstance(data, dict):
                data.update({
                    "alsa_device": alsa_device,
                    "bluetooth_device": bluetooth_device
                })
            return {
                "code": 0,
                "msg": result_data.get('msg', 'ok'),
                "data": data
            }

        # 返回错误响应
        return result_data if result_data else {"code": -1, "msg": "Unknown error", "data": None}


# 全局实例
media_mgr = MediaMgr()

