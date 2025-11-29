'''
小米设备管理路由
'''
from flask import Blueprint, request
from core.log_config import root_logger
from core.device.mi_device import scan_devices_sync

log = root_logger()
mi_bp = Blueprint('mi', __name__)


def _ok(data=None):
    return {"code": 0, "msg": "ok", "data": data}


def _err(message: str):
    return {"code": -1, "msg": message}


@mi_bp.route("/mi/scan", methods=['GET'])
def mi_scan():
    """扫描小米设备"""
    try:
        timeout = request.args.get('timeout', 5.0, type=float)
        log.info(f"===== [MI Scan] timeout={timeout}")
        devices = scan_devices_sync(timeout)
        return _ok(devices)
    except Exception as e:
        log.error(f"[MI] Scan error: {e}")
        return _err(f'error: {str(e)}')

