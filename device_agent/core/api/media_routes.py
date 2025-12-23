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
    GET /media/status
    """
    log.info("===== [Media Status]")
    status = media_mgr.get_status()
    return _ok(data=status)


@media_bp.route("/media/stop", methods=['POST'])
@handle_errors("停止媒体播放")
def media_stop():
    """
    停止当前正在播放的音频
    POST /media/stop
    """
    log.info("===== [Media Stop]")
    result = media_mgr.stop()
    return _convert_result(result)


@media_bp.route("/media/play", methods=['POST'])
@handle_errors("播放媒体文件")
def media_play():
    """
    直接播放指定的音频文件
    POST /media/play
    {
        "file_path": "/path/to/file.mp3",
        "device_address": "XX:XX:XX:XX:XX:XX",  # 可选
        "alsa_device": "bluealsa:..."  # 可选
    }
    """
    log.info("===== [Media Play File]")

    # 从请求体获取参数
    args = request.get_json() or {}
    file_path = args.get('file_path')
    device_address = args.get('device_address')
    alsa_device = args.get('alsa_device')

    if not file_path:
        return _err(msg="file_path is required")

    # 检查文件是否存在
    if not os.path.exists(file_path):
        return _err(msg=f"File not found: {file_path}")

    # 使用 MediaMgr 播放文件
    result = media_mgr.play(file_path, device_address, alsa_device)
    return _convert_result(result)


