'''
蓝牙设备管理路由
'''
from flask import Blueprint, json, request
from core.log_config import root_logger
from core.config import config_mgr
from core.utils import _ok, _err, _convert_result
from core.service.bluetooth_mgr import bluetooth_mgr

log = root_logger()
bluetooth_bp = Blueprint('bluetooth', __name__)


@bluetooth_bp.route("/bluetooth/scan", methods=['GET'])
def bluetooth_scan():
    """
    扫描蓝牙设备
    GET /bluetooth/scan?timeout=5&adapter=hci0
    """
    try:
        timeout = request.args.get('timeout', 5.0, type=float)
        adapter = request.args.get('adapter', None)
        log.info(f"===== [Bluetooth Scan] timeout={timeout}, adapter={adapter}")
        devices = bluetooth_mgr.scan_devices_sync(timeout, adapter)
        return _ok(data=devices)
    except Exception as e:
        log.error(e)
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/connect", methods=['POST'])
def bluetooth_connect():
    """
    连接蓝牙设备
    POST /bluetooth/connect
    {
        "address": "XX:XX:XX:XX:XX:XX",
        "adapter": "hci0"  # 可选
    }
    """
    try:
        args = request.get_json()
        log.info("===== [Bluetooth Connect] " + json.dumps(args))
        address = args.get('address')
        adapter = args.get('adapter')
        if not address:
            return _err(msg="address is required")
        result = bluetooth_mgr.connect_device_sync(address, adapter=adapter)
        return _convert_result(result)
    except Exception as e:
        log.error(e)
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/disconnect", methods=['POST'])
def bluetooth_disconnect():
    """
    断开蓝牙设备
    POST /bluetooth/disconnect
    {
        "address": "XX:XX:XX:XX:XX:XX",
        "adapter": "hci0"  # 可选
    }
    """
    try:
        args = request.get_json()
        log.info("===== [Bluetooth Disconnect] " + json.dumps(args))
        address = args.get('address')
        adapter = args.get('adapter')
        if not address:
            return _err(msg="address is required")
        result = bluetooth_mgr.disconnect_device_sync(address, adapter=adapter)
        return _convert_result(result)
    except Exception as e:
        log.error(e)
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/trust", methods=['POST'])
def bluetooth_trust():
    """
    信任蓝牙设备
    POST /bluetooth/trust
    {
        "address": "XX:XX:XX:XX:XX:XX",
        "adapter": "hci0"  # 可选
    }
    """
    try:
        args = request.get_json()
        log.info("===== [Bluetooth Trust] " + json.dumps(args))
        address = args.get('address')
        adapter = args.get('adapter')
        if not address:
            return _err(msg="address is required")
        result = bluetooth_mgr.trust_device(address, adapter)
        return _convert_result(result)
    except Exception as e:
        log.error(e)
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/connected", methods=['GET'])
def bluetooth_get_connected():
    """
    获取所有已连接的蓝牙设备列表（包括通过 BluetoothMgr 连接的和系统级别连接的）
    GET /bluetooth/connected?adapter=hci0
    """
    try:
        adapter = request.args.get('adapter', None)
        log.info(f"===== [Bluetooth Get Connected Devices] adapter={adapter}")
        devices = bluetooth_mgr.get_connected_devices(adapter)
        return _ok(data=devices)
    except Exception as e:
        log.error(e)
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/paired", methods=['GET'])
def bluetooth_get_paired():
    """
    获取系统已配对的蓝牙设备列表（别名接口）
    GET /bluetooth/paired?adapter=hci0
    """
    try:
        adapter = request.args.get('adapter', None)
        log.info(f"===== [Bluetooth Get Paired Devices] adapter={adapter}")
        devices = bluetooth_mgr.get_paired_devices(adapter)
        return _ok(data=devices)
    except Exception as e:
        log.error(e)
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/info", methods=['GET'])
def bluetooth_get_info():
    """
    获取指定蓝牙设备的信息
    GET /bluetooth/info?address=XX:XX:XX:XX:XX:XX&adapter=hci0
    """
    try:
        address = request.args.get('address')
        adapter = request.args.get('adapter', None)
        if not address:
            return _err(msg="address 参数是必需的")
        
        log.info(f"===== [Bluetooth Get Info] address={address}, adapter={adapter}")
        result = bluetooth_mgr.get_info(address, adapter)
        return _convert_result(result)
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
        default_address = config_mgr.get_default_bluetooth_device()

        if not default_address:
            return _ok(data=None, msg="未设置默认设备")

        # 尝试获取设备详细信息
        device_info = None
        try:
            devices = bluetooth_mgr.get_paired_devices()
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
        success = config_mgr.set_default_bluetooth_device(address)

        if not success:
            return _err(msg="保存配置失败")

        log.info(f"默认蓝牙设备已设置为: {address}")

        return _ok(data={
            "address": address
        }, msg="默认蓝牙设备已设置")
    except Exception as e:
        log.error(f"设置默认蓝牙设备失败: {e}")
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/adapters", methods=['GET'])
def bluetooth_get_adapters():
    """
    获取所有可用的蓝牙适配器列表
    GET /bluetooth/adapters
    """
    try:
        log.info("===== [Bluetooth Get Adapters]")
        adapters = bluetooth_mgr.get_adapters()
        default_adapter = bluetooth_mgr.get_default_adapter()
        return _ok(data={
            "adapters": adapters,
            "default_adapter": default_adapter
        })
    except Exception as e:
        log.error(f"获取蓝牙适配器列表失败: {e}")
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/adapter/default", methods=['GET'])
def bluetooth_get_default_adapter():
    """
    获取默认蓝牙适配器
    GET /bluetooth/adapter/default
    """
    try:
        log.info("===== [Bluetooth Get Default Adapter]")
        default_adapter = bluetooth_mgr.get_default_adapter()
        adapters = bluetooth_mgr.get_adapters()
        adapter_info = next((a for a in adapters if a.get('name') == default_adapter), None)
        
        return _ok(data={
            "adapter": default_adapter,
            "adapter_info": adapter_info
        })
    except Exception as e:
        log.error(f"获取默认蓝牙适配器失败: {e}")
        return _err(msg=f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/adapter/default", methods=['POST'])
def bluetooth_set_default_adapter():
    """
    设置默认蓝牙适配器
    POST /bluetooth/adapter/default
    {
        "adapter": "hci0"
    }
    """
    try:
        args = request.get_json()
        log.info(f"===== [Bluetooth Set Default Adapter] {json.dumps(args)}")

        adapter = args.get('adapter')
        if not adapter:
            return _err(msg="adapter 参数是必需的")

        result = bluetooth_mgr.set_default_adapter(adapter)
        return _convert_result(result)
    except Exception as e:
        log.error(f"设置默认蓝牙适配器失败: {e}")
        return _err(msg=f'error: {str(e)}')
