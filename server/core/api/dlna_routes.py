'''
DLNA设备管理路由
'''
from flask import Blueprint, request
from core.log_config import root_logger
from core.device.dlna import DlnaMgr

log = root_logger()
dlna_bp = Blueprint('dlna', __name__)


@dlna_bp.route("/dlna/scan", methods=['GET'])
def dlna_scan():
    """
    扫描DLNA设备
    """
    try:
        timeout = request.args.get('timeout', 5.0, type=float)
        log.info(f"===== [DLNA Scan] timeout={timeout}")
        device_list = DlnaMgr.scan_devices(timeout)
        return {"code": 0, "msg": "ok", "data": device_list}
    except Exception as e:
        log.error(f"[DLNA] Scan error: {e}")
        return {"code": -1, "msg": 'error: ' + str(e)}
