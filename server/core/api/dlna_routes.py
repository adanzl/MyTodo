'''
DLNA设备管理路由
'''
from flask import Blueprint, request
from core.log_config import root_logger
from core.device.dlna import scan_devices_sync, DlnaDev
from core.utils import _ok, _err, read_json_from_request

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


@dlna_bp.route("/dlna/volume", methods=['GET', 'POST'])
def dlna_volume():
    """获取或设置DLNA设备音量"""
    try:
        location = request.args.get('location') or (request.json or {}).get('location')
        if not location:
            return _err('location is required')

        device = DlnaDev(location)

        if request.method == 'GET':
            # 获取音量
            code, volume = device.get_volume()
            if code == 0:
                return _ok({'volume': volume})
            else:
                return _err(f'获取音量失败')
        else:
            # 设置音量
            volume = (request.json or {}).get('volume')
            if volume is None:
                return _err('volume is required')

            volume = int(volume)
            if volume < 0 or volume > 100:
                return _err('volume must be between 0 and 100')

            code, msg = device.set_volume(volume)
            if code == 0:
                return _ok({'volume': volume})
            else:
                return _err(msg or '设置音量失败')
    except Exception as e:
        log.error(f"[DLNA] Volume error: {e}")
        return _err(f'error: {str(e)}')
