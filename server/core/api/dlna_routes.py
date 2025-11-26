'''
DLNA设备管理路由
'''
from flask import Blueprint, request
from core.log_config import root_logger
from core.device.dlna import scan_devices_sync

log = root_logger()
dlna_bp = Blueprint('dlna', __name__)


def _ok(data=None):
    return {"code": 0, "msg": "ok", "data": data}


def _err(message: str):
    return {"code": -1, "msg": message}


@dlna_bp.route("/dlna/scan", methods=['GET'])
def dlna_scan():
    """扫描DLNA设备"""
    try:
        timeout = request.args.get('timeout', 5.0, type=float)
        log.info(f"===== [DLNA Scan] timeout={timeout}")
        return _ok(scan_devices_sync(timeout))
    except Exception as e:
        log.error(f"[DLNA] Scan error: {e}")
        return _err(f'error: {str(e)}')
