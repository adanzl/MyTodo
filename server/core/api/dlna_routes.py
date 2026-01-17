"""DLNA 设备管理路由。"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from core.config import app_logger
from core.device.dlna import DlnaDev, scan_devices_sync
from core.utils import _err, _ok, read_json_from_request, get_json_body

log = app_logger
dlna_bp = Blueprint('dlna', __name__)


@dlna_bp.route("/dlna/scan", methods=['GET'])
def dlna_scan() -> ResponseReturnValue:
    """扫描 DLNA 设备。"""
    try:
        timeout = request.args.get('timeout', 5.0, type=float)
        log.info(f"===== [DLNA Scan] timeout={timeout}")
        return _ok(scan_devices_sync(timeout))
    except Exception as e:
        log.error(f"[DLNA] Scan error: {e}")
        return _err(f'error: {str(e)}')


@dlna_bp.route("/dlna/volume", methods=['GET', 'POST'])
def dlna_volume() -> ResponseReturnValue:
    """获取或设置 DLNA 设备音量。"""
    try:
        body = get_json_body()
        location = request.args.get('location') or body.get('location')
        if not location:
            return _err('location is required')

        device = DlnaDev(location)

        if request.method == 'GET':
            code, volume = device.get_volume()
            if code == 0:
                return _ok({'volume': volume})
            else:
                return _err('获取音量失败')
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
        log.error(f"[DLNA] Volume error: {e}")
        return _err(f'error: {str(e)}')


@dlna_bp.route("/dlna/stop", methods=['POST'])
def dlna_stop() -> ResponseReturnValue:
    """停止 DLNA 设备播放。"""
    try:
        data: Dict[str, Any] = read_json_from_request()
        location = data.get('location')
        if not location:
            return _err('location is required')

        device = DlnaDev(location)
        code, msg = device.stop()
        if code == 0:
            return _ok({'message': msg or '停止成功'})
        else:
            return _err(msg or '停止失败')
    except Exception as e:
        log.error(f"[DLNA] Stop error: {e}")
        return _err(f'error: {str(e)}')
