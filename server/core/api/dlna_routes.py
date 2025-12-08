'''
DLNA设备管理路由
'''
from flask import Blueprint, request
from core.log_config import root_logger
from core.device.dlna import scan_devices_sync
from core.utils import _ok, _err

log = root_logger()
dlna_bp = Blueprint('dlna', __name__)


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
