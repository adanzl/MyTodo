'''
蓝牙设备管理路由
'''
from flask import Blueprint, json, request
from core.log_config import root_logger
from core.config import get_config
from core.utils import _ok, _err, _convert_result
from core.device.bluetooth import (
    scan_devices_sync,
    connect_device_sync,
    disconnect_device_sync,
    get_system_paired_devices_sync,
)

log = root_logger()
bluetooth_bp = Blueprint('bluetooth', __name__)


@bluetooth_bp.route("/bluetooth/scan", methods=['GET'])
def bluetooth_scan():
    """
    扫描蓝牙设备
    """
    try:
        timeout = request.args.get('timeout', 5.0, type=float)
        log.info(f"===== [Bluetooth Scan] timeout={timeout}")
        devices = scan_devices_sync(timeout)
        return _ok(data=devices)
    except Exception as e:
        log.error(e)
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/connect", methods=['POST'])
def bluetooth_connect():
    """
    连接蓝牙设备
    """
    try:
        args = request.get_json()
        log.info("===== [Bluetooth Connect] " + json.dumps(args))
        address = args.get('address')
        if not address:
            return _err(msg="address is required")
        result = connect_device_sync(address)
        return _convert_result(result)
    except Exception as e:
        log.error(e)
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/disconnect", methods=['POST'])
def bluetooth_disconnect():
    """
    断开蓝牙设备
    """
    try:
        args = request.get_json()
        log.info("===== [Bluetooth Disconnect] " + json.dumps(args))
        address = args.get('address')
        if not address:
            return _err(msg="address is required")
        result = disconnect_device_sync(address)
        return _convert_result(result)
    except Exception as e:
        log.error(e)
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/connected", methods=['GET'])
def bluetooth_get_connected():
    """
    获取系统已连接的蓝牙设备列表
    """
    try:
        log.info("===== [Bluetooth Get Connected Devices]")
        devices = get_system_paired_devices_sync()
        return _ok(data=devices)
    except Exception as e:
        log.error(e)
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/paired", methods=['GET'])
def bluetooth_get_paired():
    """
    获取系统已配对的蓝牙设备列表（别名接口）
    """
    try:
        log.info("===== [Bluetooth Get Paired Devices]")
        devices = get_system_paired_devices_sync()
        return _ok(data=devices)
    except Exception as e:
        log.error(e)
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/default", methods=['GET'])
def bluetooth_get_default():
    """
    获取默认蓝牙设备
    """
    try:
        log.info("===== [Bluetooth Get Default Device]")
        config = get_config()
        default_address = config.get_default_bluetooth_device()
        
        if not default_address:
            return _ok(data=None, msg="未设置默认设备")
        
        # 尝试获取设备详细信息
        device_info = None
        try:
            devices = get_system_paired_devices_sync()
            device_info = next(
                (d for d in devices if d.get('address', '').upper() == default_address.upper()),
                None
            )
        except Exception as e:
            log.warning(f"获取设备信息失败: {e}")
        
        return _ok(data={
            "address": default_address,
            "device_info": device_info
        })
    except Exception as e:
        log.error(f"获取默认蓝牙设备失败: {e}")
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/setDefault", methods=['POST'])
def bluetooth_set_default():
    """
    设置默认蓝牙设备
    """
    try:
        args = request.get_json()
        log.info(f"===== [Bluetooth Set Default Device] {json.dumps(args)}")
        
        address = args.get('address')
        if not address:
            return _err(msg="address 参数是必需的")
        
        # 验证地址格式（简单验证）
        address = address.strip().upper()
        if len(address.replace(':', '')) != 12:
            return _err(msg="蓝牙设备地址格式不正确")
        
        # 保存到配置
        config = get_config()
        success = config.set_default_bluetooth_device(address)
        
        if not success:
            return _err(msg="保存配置失败")
        
        log.info(f"默认蓝牙设备已设置为: {address}")
        
        return _ok(data={
            "address": address
        }, msg="默认蓝牙设备已设置")
    except Exception as e:
        log.error(f"设置默认蓝牙设备失败: {e}")
        return _err(msg=f'error: {str(e)}')
