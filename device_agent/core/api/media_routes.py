'''
媒体管理路由
'''
import os
from functools import wraps
from typing import Any, Callable
from flask import Blueprint, request
from core.log_config import root_logger
from core.utils import _ok, _err, _convert_result
from core.service.media_mgr import media_mgr

log = root_logger()
media_bp = Blueprint('media', __name__)


def handle_errors(operation_name: str):
    """
    错误处理装饰器，统一处理路由函数的异常
    :param operation_name: 操作名称，用于日志记录
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log.error(f"[MEDIA] {operation_name}失败: {e}", exc_info=True)
                return _err(msg=f'{operation_name}失败: {str(e)}')
        return wrapper
    return decorator


@media_bp.route("/media/status", methods=['GET'])
@handle_errors("获取媒体播放状态")
def media_status():
    """
    获取当前媒体播放状态
    GET /media/status?device_address=XX:XX:XX:XX:XX:XX
    如果不指定 device_address，返回所有设备的状态
    """
    log.info("===== [Media Status]")
    device_address = request.args.get('device_address')
    status = media_mgr.get_status(device_address)
    return _convert_result(status)


@media_bp.route("/media/stop", methods=['POST'])
@handle_errors("停止媒体播放")
def media_stop():
    """
    停止媒体播放
    POST /media/stop
    {
        "device_address": "XX:XX:XX:XX:XX:XX"  # 可选，如果不指定则停止所有设备
    }
    """
    log.info("===== [Media Stop]")
    args = request.get_json() or {}
    device_address = args.get('device_address')
    result = media_mgr.stop(device_address)
    return _convert_result(result)


@media_bp.route("/media/play", methods=['POST'])
@handle_errors("播放媒体文件")
def media_play():
    """
    播放指定的音频文件
    POST /media/play
    {
        "file_path": "/path/to/file.mp3",
        "device_address": "XX:XX:XX:XX:XX:XX",  # 可选
        "alsa_device": "bluealsa:...",  # 可选
        "hci_adapter": "hci0",  # 可选，默认 hci0
        "position": 0.0  # 可选，起始位置（秒），默认 0.0
    }
    """
    log.info("===== [Media Play File]")

    # 从请求体获取参数
    args = request.get_json() or {}
    file_path = args.get('file_path')
    device_address = args.get('device_address')
    alsa_device = args.get('alsa_device')
    hci_adapter = args.get('hci_adapter', 'hci0')
    position = args.get('position', 0.0)

    if not file_path:
        return _err(msg="file_path is required")

    # 检查文件是否存在
    if not os.path.exists(file_path):
        return _err(msg=f"File not found: {file_path}")

    # 使用 MediaMgr 播放文件
    result = media_mgr.play(file_path, device_address, alsa_device, hci_adapter, position)
    return _convert_result(result)


@media_bp.route("/media/pause", methods=['POST'])
@handle_errors("暂停媒体播放")
def media_pause():
    """
    暂停媒体播放
    POST /media/pause
    {
        "device_address": "XX:XX:XX:XX:XX:XX"  # 必需
    }
    """
    log.info("===== [Media Pause]")
    args = request.get_json() or {}
    device_address = args.get('device_address')
    
    if not device_address:
        return _err(msg="device_address is required")
    
    result = media_mgr.pause(device_address)
    return _convert_result(result)


@media_bp.route("/media/resume", methods=['POST'])
@handle_errors("恢复媒体播放")
def media_resume():
    """
    恢复媒体播放
    POST /media/resume
    {
        "device_address": "XX:XX:XX:XX:XX:XX"  # 必需
    }
    """
    log.info("===== [Media Resume]")
    args = request.get_json() or {}
    device_address = args.get('device_address')
    
    if not device_address:
        return _err(msg="device_address is required")
    
    result = media_mgr.resume(device_address)
    return _convert_result(result)


@media_bp.route("/media/seek", methods=['POST'])
@handle_errors("跳转播放位置")
def media_seek():
    """
    跳转播放位置
    POST /media/seek
    {
        "device_address": "XX:XX:XX:XX:XX:XX",  # 必需
        "position": 30.0  # 必需，位置（秒）或比例（0.0-1.0）
    }
    """
    log.info("===== [Media Seek]")
    args = request.get_json() or {}
    device_address = args.get('device_address')
    position = args.get('position')
    
    if not device_address:
        return _err(msg="device_address is required")
    
    if position is None:
        return _err(msg="position is required")
    
    try:
        position = float(position)
    except (ValueError, TypeError):
        return _err(msg="position must be a number")
    
    result = media_mgr.seek(device_address, position)
    return _convert_result(result)


@media_bp.route("/media/volume", methods=['POST'])
@handle_errors("设置音量")
def media_volume():
    """
    设置音量
    POST /media/volume
    {
        "device_address": "XX:XX:XX:XX:XX:XX",  # 必需
        "volume": 50  # 必需，音量 0-100
    }
    """
    log.info("===== [Media Set Volume]")
    args = request.get_json() or {}
    device_address = args.get('device_address')
    volume = args.get('volume')
    
    if not device_address:
        return _err(msg="device_address is required")
    
    if volume is None:
        return _err(msg="volume is required")
    
    try:
        volume = int(volume)
        if volume < 0 or volume > 100:
            return _err(msg="volume must be between 0 and 100")
    except (ValueError, TypeError):
        return _err(msg="volume must be a number")
    
    result = media_mgr.set_volume(device_address, volume)
    return _convert_result(result)


