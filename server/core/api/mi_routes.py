"""小米设备管理路由。"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from core.config import app_logger
from core.device.mi_device import MiDevice, scan_devices_sync
from core.utils import _err, _ok, read_json_from_request, get_json_body

log = app_logger
mi_bp = Blueprint('mi', __name__)


@mi_bp.route("/mi/scan", methods=['GET'])
def mi_scan() -> ResponseReturnValue:
    """扫描小米设备（同步模式）。"""
    try:
        timeout = request.args.get('timeout', 5.0, type=float)
        log.info(f"===== [MI Scan] timeout={timeout}")
        devices = scan_devices_sync(timeout)
        return _ok(devices)
    except Exception as e:
        log.error(f"[MI] Scan error: {e}")
        return _err(f'error: {str(e)}')


@mi_bp.route("/mi/volume", methods=['GET', 'POST'])
def mi_volume() -> ResponseReturnValue:
    """获取或设置小米设备音量。"""
    try:
        body = get_json_body()
        device_id = request.args.get('device_id') or body.get('device_id')
        if not device_id:
            return _err('device_id is required')

        device = MiDevice(device_id)

        if request.method == 'GET':
            code, volume = device.get_volume()
            if code == 0:
                return _ok({'volume': volume})
            else:
                return _err(f'获取音量失败: {volume}')
        else:
            volume = body.get('volume')
            if volume is None:
                return _err('volume is required')

            try:
                volume_i = int(volume)
            except (TypeError, ValueError):
                return _err('volume must be int')

            if volume_i < 0 or volume_i > 100:
                return _err('volume must be between 0 and 100')

            code, msg = device.set_volume(volume_i)
            if code == 0:
                return _ok({'volume': volume_i})
            else:
                return _err(msg or '设置音量失败')
    except Exception as e:
        log.error(f"[MI] Volume error: {e}")
        return _err(f'error: {str(e)}')


@mi_bp.route("/mi/status", methods=['GET'])
def mi_status() -> ResponseReturnValue:
    """获取小米设备播放状态。"""
    try:
        device_id = request.args.get('device_id')
        if not device_id:
            return _err('device_id is required')

        device = MiDevice(device_id)
        code, status = device.get_status()
        if code == 0:
            return _ok(status)
        else:
            return _err(status.get('error', '获取状态失败') if isinstance(status, dict) else '获取状态失败')
    except Exception as e:
        log.error(f"[MI] Status error: {e}")
        return _err(f'error: {str(e)}')


@mi_bp.route("/mi/stop", methods=['POST'])
def mi_stop() -> ResponseReturnValue:
    """停止小米设备播放。"""
    try:
        data: Dict[str, Any] = read_json_from_request()
        device_id = data.get('device_id')
        if not device_id:
            return _err('device_id is required')

        device = MiDevice(device_id)
        code, msg = device.stop()
        if code == 0:
            return _ok({'message': msg or '停止成功'})
        else:
            return _err(msg or '停止失败')
    except Exception as e:
        log.error(f"[MI] Stop error: {e}")
        return _err(f'error: {str(e)}')
