'''
蓝牙设备管理路由
通过调用 device_agent 服务接口实现
'''
from flask import Blueprint, json, request
from core.log_config import root_logger
from core.utils import _ok, _err, read_json_from_request
from core.device.bluetooth import (
    scan_devices_sync,
    connect_device_sync,
    disconnect_device_sync,
    bluetooth_mgr,
    get_system_paired_devices_sync,
)

log = root_logger()
bluetooth_bp = Blueprint('bluetooth', __name__)

@bluetooth_bp.route("/bluetooth/scan", methods=['GET'])
def bluetooth_scan():
    """
    扫描蓝牙设备（通过 device_agent 服务）
    """
    try:
        timeout = request.args.get('timeout', 5.0, type=float)
        log.info(f"===== [Bluetooth Scan] timeout={timeout}")
        devices = scan_devices_sync(timeout)
        return _ok(devices)
    except Exception as e:
        log.error(f"[Bluetooth] Scan error: {e}")
        return _err(f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/device", methods=['GET'])
def bluetooth_get_device():
    """
    获取设备信息（通过 device_agent 服务）
    """
    try:
        address = request.args.get('address')
        log.info(f"===== [Bluetooth Get Device] address={address}")
        if not address:
            return _err("address is required")
        device = bluetooth_mgr.get_device(address)
        if device:
            return _ok(device)
        return _err("device not found")
    except Exception as e:
        log.error(f"[Bluetooth] Get device error: {e}")
        return _err(f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/connect", methods=['POST'])
def bluetooth_connect():
    """
    连接蓝牙设备（通过 device_agent 服务）
    """
    try:
        args = read_json_from_request()
        log.info(f"===== [Bluetooth Connect] {json.dumps(args)}")
        address = args.get('address')
        if not address:
            return _err("address is required")
        result = connect_device_sync(address)
        # 如果 result 已经是标准格式，直接返回；否则包装
        if isinstance(result, dict) and 'code' in result:
            return result
        return _ok(result)
    except Exception as e:
        log.error(f"[Bluetooth] Connect error: {e}")
        return _err(f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/disconnect", methods=['POST'])
def bluetooth_disconnect():
    """
    断开蓝牙设备（通过 device_agent 服务）
    """
    try:
        args = read_json_from_request()
        log.info(f"===== [Bluetooth Disconnect] {json.dumps(args)}")
        address = args.get('address')
        if not address:
            return _err("address is required")
        result = disconnect_device_sync(address)
        # 如果 result 已经是标准格式，直接返回；否则包装
        if isinstance(result, dict) and 'code' in result:
            return result
        return _ok(result)
    except Exception as e:
        log.error(f"[Bluetooth] Disconnect error: {e}")
        return _err(f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/paired", methods=['GET'])
def bluetooth_get_paired():
    """
    获取系统已配对的蓝牙设备列表（通过 device_agent 服务）
    """
    try:
        log.info("===== [Bluetooth Get Paired Devices]")
        devices = get_system_paired_devices_sync()
        return _ok(devices)
    except Exception as e:
        log.error(f"[Bluetooth] Get paired devices error: {e}")
        return _err(f'error: {str(e)}')
