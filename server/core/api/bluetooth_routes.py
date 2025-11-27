'''
蓝牙设备管理路由
通过调用 device_agent 服务接口实现
'''
from flask import Blueprint, json, request
from core.log_config import root_logger
from core.device.agent import DeviceAgent

log = root_logger()
bluetooth_bp = Blueprint('bluetooth', __name__)
device_agent = DeviceAgent()

@bluetooth_bp.route("/bluetooth/scan", methods=['GET'])
def bluetooth_scan():
    """
    扫描蓝牙设备（通过 device_agent 服务）
    """
    try:
        timeout = request.args.get('timeout', 5.0, type=float)
        log.info(f"===== [Bluetooth Scan] timeout={timeout}")
        result = device_agent.bluetooth_scan(timeout)
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/devices", methods=['GET'])
def bluetooth_get_devices():
    """
    获取设备列表（通过 device_agent 服务）
    """
    try:
        log.info("===== [Bluetooth Get Devices]")
        result = device_agent.bluetooth_get_devices()
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/device", methods=['GET'])
def bluetooth_get_device():
    """
    获取设备信息（通过 device_agent 服务）
    """
    try:
        address = request.args.get('address')
        log.info(f"===== [Bluetooth Get Device] address={address}")
        if not address:
            return {"code": -1, "msg": "address is required"}
        result = device_agent.bluetooth_get_device(address)
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/connect", methods=['POST'])
def bluetooth_connect():
    """
    连接蓝牙设备（通过 device_agent 服务）
    """
    try:
        args = request.get_json()
        log.info("===== [Bluetooth Connect] " + json.dumps(args))
        address = args.get('address')
        if not address:
            return {"code": -1, "msg": "address is required"}
        result = device_agent.bluetooth_connect(address)
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/disconnect", methods=['POST'])
def bluetooth_disconnect():
    """
    断开蓝牙设备（通过 device_agent 服务）
    """
    try:
        args = request.get_json()
        log.info("===== [Bluetooth Disconnect] " + json.dumps(args))
        address = args.get('address')
        if not address:
            return {"code": -1, "msg": "address is required"}
        result = device_agent.bluetooth_disconnect(address)
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/connected", methods=['GET'])
def bluetooth_get_connected():
    """
    获取系统已连接的蓝牙设备列表（通过 device_agent 服务）
    """
    try:
        log.info("===== [Bluetooth Get Connected Devices]")
        result = device_agent.bluetooth_get_connected()
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}
