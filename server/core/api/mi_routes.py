'''
小米设备管理路由
'''
from flask import Blueprint, request
from core.log_config import root_logger
from core.device.mi_device import scan_devices_sync, MiDevice
from core.utils import _ok, _err

log = root_logger()
mi_bp = Blueprint('mi', __name__)


@mi_bp.route("/mi/scan", methods=['GET'])
def mi_scan():
    """扫描小米设备（同步模式，gevent 不会阻塞其他请求）"""
    try:
        timeout = request.args.get('timeout', 5.0, type=float)
        log.info(f"===== [MI Scan] timeout={timeout}")
        devices = scan_devices_sync(timeout)
        return _ok(devices)
    except Exception as e:
        log.error(f"[MI] Scan error: {e}")
        return _err(f'error: {str(e)}')


@mi_bp.route("/mi/volume", methods=['GET', 'POST'])
def mi_volume():
    """获取或设置小米设备音量"""
    try:
        device_id = request.args.get('device_id') or (request.json or {}).get('device_id')
        if not device_id:
            return _err('device_id is required')

        device = MiDevice(device_id)

        if request.method == 'GET':
            # 获取音量
            code, volume = device.get_volume()
            if code == 0:
                return _ok({'volume': volume})
            else:
                return _err(f'获取音量失败: {volume}')
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
        log.error(f"[MI] Volume error: {e}")
        return _err(f'error: {str(e)}')
