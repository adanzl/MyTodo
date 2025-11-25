'''
媒体管理路由
'''
import os
import time
import subprocess
from flask import Blueprint, request
from core.log_config import root_logger
from core.device.bluetooth import connect_device_sync, get_bluetooth_mgr

log = root_logger()
media_bp = Blueprint('media', __name__)

# 当前播放进程（用于 mpg123）
_current_playback_process = None


def get_alsa_bluetooth_device(device_address=None, hci_adapter='hci0'):
    """
    获取 ALSA 蓝牙音频设备名称（直接根据 MAC 地址构造）
    :param device_address: 蓝牙设备地址（可选）
    :param hci_adapter: HCI 适配器名称，默认为 hci0
    :return: ALSA 设备名称，例如 "bluealsa:HCI=hci0,DEV=XX:XX:XX:XX:XX:XX,PROFILE=a2dp"
    """
    try:
        # 1. 从蓝牙管理器获取已配对的设备
        bt_mgr = get_bluetooth_mgr()
        paired_devices = bt_mgr.get_system_paired_devices()
        
        if not paired_devices:
            log.warning("[MEDIA] No paired bluetooth devices found")
            return None
        
        # 2. 确定目标蓝牙设备
        target_device = None
        if device_address:
            # 查找指定地址的设备
            addr_upper = device_address.upper()
            for device in paired_devices:
                if device.get('address', '').upper() == addr_upper:
                    target_device = device
                    break
            
            if not target_device:
                log.warning(f"[MEDIA] Bluetooth device not found: {device_address}")
                # 即使没找到设备信息，仍然尝试构造 ALSA 设备名
                target_device = {'address': device_address, 'name': device_address, 'connected': False}
        else:
            # 使用第一个已连接的设备
            for device in paired_devices:
                if device.get('connected'):
                    target_device = device
                    break
            
            if not target_device:
                log.warning("[MEDIA] No connected bluetooth devices found")
                # 如果没有已连接的，使用第一个已配对的
                target_device = paired_devices[0]
                log.info(f"[MEDIA] Using first paired device: {target_device.get('name')}")
        
        device_address = target_device.get('address')
        device_name = target_device.get('name', device_address)
        is_connected = target_device.get('connected', False)
        
        # 检查设备是否已连接
        if not is_connected:
            log.warning(f"[MEDIA] Bluetooth device not connected: {device_name} ({device_address})")
        else:
            log.info(f"[MEDIA] Target bluetooth device: {device_name} ({device_address})")
        
        # 3. 直接根据 MAC 地址构造 bluealsa ALSA 设备名称
        # 格式: bluealsa:HCI=hci0,DEV=XX:XX:XX:XX:XX:XX,PROFILE=a2dp
        alsa_device = f"bluealsa:HCI={hci_adapter},DEV={device_address.upper()},PROFILE=a2dp"
        
        log.info(f"[MEDIA] Using ALSA device: {alsa_device}")
        return alsa_device
        
    except Exception as e:
        log.error(f"[MEDIA] Error getting ALSA device: {e}")
        return None


def stop_current_playback():
    """
    停止当前正在播放的音频
    :return: 停止结果
    """
    global _current_playback_process
    
    try:
        # 停止 mpg123 播放进程
        if _current_playback_process and _current_playback_process.poll() is None:
            # 进程还在运行
            log.info(f"[MEDIA] Terminating playback process (PID: {_current_playback_process.pid})")
            _current_playback_process.terminate()
            try:
                _current_playback_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                log.warning("[MEDIA] Process did not terminate, killing it")
                _current_playback_process.kill()
                _current_playback_process.wait()
            _current_playback_process = None
            log.info("[MEDIA] Stopped playback process")
            return {"code": 0, "msg": "Playback stopped"}
        else:
            return {"code": 0, "msg": "No playback in progress"}
            
    except Exception as e:
        log.error(f"[MEDIA] Error stopping playback: {e}")
        return {"code": -1, "msg": f"Stop failed: {str(e)}"}


def play_media_file_with_mpg123(file_path, alsa_device=None):
    """
    使用 mpg123 播放音频文件
    :param file_path: 文件路径
    :param alsa_device: ALSA 设备名称（例如 "bluealsa:HCI=hci0,DEV=XX:XX:XX:XX:XX:XX,PROFILE=a2dp"）
    :return: 播放结果
    """
    try:
        # 构建 mpg123 命令
        cmd = ['mpg123']
        
        # 如果指定了 ALSA 设备，添加输出参数
        if alsa_device:
            cmd.extend(['-a', alsa_device])
        
        # 添加文件路径
        cmd.append(file_path)
        
        log.info(f"[MEDIA]: {' '.join(cmd)}")
        
        # 准备环境变量 - 继承当前环境并确保包含必要的音频相关变量
        env = os.environ.copy()
        
        # 确保 XDG_RUNTIME_DIR 存在（对于某些音频系统很重要）
        if 'XDG_RUNTIME_DIR' not in env:
            # 尝试设置默认值
            import pwd
            try:
                user_info = pwd.getpwuid(os.getuid())
                env['XDG_RUNTIME_DIR'] = f"/run/user/{os.getuid()}"
            except:
                pass
        
        # 确保 HOME 环境变量存在
        if 'HOME' not in env:
            try:
                import pwd
                user_info = pwd.getpwuid(os.getuid())
                env['HOME'] = user_info.pw_dir
            except:
                pass
        
        # 后台启动播放进程，使用完整的环境变量
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True  # 在新会话中启动，避免继承信号
        )
        
        # 保存进程引用以便后续停止
        global _current_playback_process
        _current_playback_process = process
        
        log.info(f"[MEDIA] Started playback: {file_path} (PID: {process.pid})")
        
        # 等待一小段时间检查进程是否立即退出（可能是错误）
        time.sleep(0.1)
        if process.poll() is not None:
            # 进程已经退出，读取错误信息
            stdout, stderr = process.communicate()
            log.error(f"[MEDIA] mpg123 exited immediately. stderr: {stderr}")
            return {"code": -1, "msg": f"mpg123 failed: {stderr}"}
        
        return {"code": 0, "msg": "Playing", "file": os.path.basename(file_path), "pid": process.pid}
        
    except FileNotFoundError:
        log.error("[MEDIA] mpg123 not found")
        return {"code": -1, "msg": "mpg123 not installed"}
    except Exception as e:
        log.error(f"[MEDIA] Error playing file: {e}")
        return {"code": -1, "msg": f"Play failed: {str(e)}"}


@media_bp.route("/media/stop", methods=['POST'])
def media_stop():
    """
    停止当前正在播放的音频
    """
    try:
        log.info("===== [Media Stop]")
        result = stop_current_playback()
        return result
    except Exception as e:
        log.error(f"[MEDIA] Stop error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}

@media_bp.route("/media/play", methods=['POST'])
def media_play_file():
    """
    直接播放指定的音频文件
    """
    try:
        log.info("===== [Media Play File]")
        
        # 从请求体获取参数
        args = request.get_json() or {}
        file_path = args.get('file_path')
        device_address = args.get('device_address')  # 可选
        alsa_device = args.get('alsa_device')  # 可选：直接指定 ALSA 设备名
        
        if not file_path:
            return {"code": -1, "msg": "file_path is required"}
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {"code": -1, "msg": f"File not found: {file_path}"}
        
        # 停止当前播放
        stop_current_playback()
        
        # 获取蓝牙设备信息（如果提供了地址）
        bluetooth_device = None
        if device_address:
            # 尝试连接设备
            connect_result = connect_device_sync(device_address, timeout=10.0)
            if connect_result.get('code') == 0:
                bluetooth_device = connect_result.get('data', {})
                log.info(f"[MEDIA] Connected to bluetooth device: {device_address}")
            else:
                log.warning(f"[MEDIA] Failed to connect: {connect_result.get('msg')}")
        
        # 如果没有直接指定 ALSA 设备，尝试获取
        if not alsa_device and device_address:
            alsa_device = get_alsa_bluetooth_device(device_address)
            if alsa_device:
                log.info(f"[MEDIA] Found ALSA device: {alsa_device}")
        elif not alsa_device:
            # 没有指定任何设备，尝试获取第一个蓝牙设备
            alsa_device = get_alsa_bluetooth_device()
            if alsa_device:
                log.info(f"[MEDIA] Using default ALSA device: {alsa_device}")
        
        # 播放文件
        result = play_media_file_with_mpg123(file_path, alsa_device)
        
        return {
            "code": result.get('code', -1),
            "msg": result.get('msg', 'Unknown error'),
            "data": {
                "file": result.get('file'),
                "pid": result.get('pid'),
                "alsa_device": alsa_device,
                "bluetooth_device": bluetooth_device
            }
        }
        
    except Exception as e:
        log.error(f"[MEDIA] Play file error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}


@media_bp.route("/media/debug", methods=['GET'])
def media_debug():
    """
    调试接口：显示环境信息和进程状态
    """
    try:
        import pwd
        import grp
        
        # 获取当前用户信息
        uid = os.getuid()
        gid = os.getgid()
        user_info = pwd.getpwuid(uid)
        group_info = grp.getgrgid(gid)
        
        # 获取用户所属的所有组
        groups = [grp.getgrgid(g).gr_name for g in os.getgroups()]
        
        # 检查音频权限
        audio_groups = [g for g in groups if 'audio' in g.lower() or 'bluetooth' in g.lower()]
        
        # 检查 mpg123 是否存在
        mpg123_path = None
        try:
            result = subprocess.run(['which', 'mpg123'], capture_output=True, text=True)
            if result.returncode == 0:
                mpg123_path = result.stdout.strip()
        except:
            pass
        
        # 获取蓝牙设备
        bt_mgr = get_bluetooth_mgr()
        paired_devices = bt_mgr.get_system_paired_devices()
        
        # 检查当前播放状态
        playback_status = "idle"
        if _current_playback_process and _current_playback_process.poll() is None:
            playback_status = f"playing (PID: {_current_playback_process.pid})"
        
        return {
            "code": 0,
            "msg": "ok",
            "data": {
                "system": {
                    "user": user_info.pw_name,
                    "uid": uid,
                    "gid": gid,
                    "home": user_info.pw_dir,
                    "shell": user_info.pw_shell,
                    "groups": groups,
                    "audio_groups": audio_groups,
                },
                "environment": {
                    "XDG_RUNTIME_DIR": os.environ.get('XDG_RUNTIME_DIR'),
                    "HOME": os.environ.get('HOME'),
                    "USER": os.environ.get('USER'),
                    "PATH": os.environ.get('PATH'),
                    "DBUS_SESSION_BUS_ADDRESS": os.environ.get('DBUS_SESSION_BUS_ADDRESS'),
                },
                "tools": {
                    "mpg123": mpg123_path,
                },
                "bluetooth": {
                    "paired_devices_count": len(paired_devices),
                    "connected_devices": [d for d in paired_devices if d.get('connected')],
                },
                "playback": {
                    "status": playback_status,
                }
            }
        }
        
    except Exception as e:
        log.error(f"[MEDIA] Debug error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}
