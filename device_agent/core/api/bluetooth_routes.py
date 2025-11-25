'''
蓝牙设备管理路由
'''
import os
import urllib.parse
from flask import Blueprint, json, request
from core.log_config import root_logger
from core.device.bluetooth import (
    get_bluetooth_mgr,
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
        return {"code": 0, "msg": "ok", "data": devices}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/devices", methods=['GET'])
def bluetooth_get_devices():
    """
    获取设备列表
    """
    try:
        log.info("===== [Bluetooth Get Devices]")
        devices = get_bluetooth_mgr().get_device_list()
        return {"code": 0, "msg": "ok", "data": devices}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/device", methods=['GET'])
def bluetooth_get_device():
    """
    获取设备信息
    """
    try:
        address = request.args.get('address')
        log.info(f"===== [Bluetooth Get Device] address={address}")
        if not address:
            return {"code": -1, "msg": "address is required"}
        device = get_bluetooth_mgr().get_device(address)
        if device:
            return {"code": 0, "msg": "ok", "data": device}
        else:
            return {"code": -1, "msg": "Device not found"}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


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
            return {"code": -1, "msg": "address is required"}
        result = connect_device_sync(address)
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


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
            return {"code": -1, "msg": "address is required"}
        result = disconnect_device_sync(address)
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/connected", methods=['GET'])
def bluetooth_get_connected():
    """
    获取系统已连接的蓝牙设备列表
    """
    try:
        log.info("===== [Bluetooth Get Connected Devices]")
        devices = get_system_paired_devices_sync()
        return {"code": 0, "msg": "ok", "data": devices}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}
