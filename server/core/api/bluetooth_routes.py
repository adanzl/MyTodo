"""蓝牙设备管理路由。
通过调用 device_agent 服务接口实现。
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, json, request
from flask.typing import ResponseReturnValue

from core.config import app_logger
from core.services.bluetooth_mgr import bluetooth_mgr
from core.utils import _err, _ok, read_json_from_request

log = app_logger
bluetooth_bp = Blueprint('bluetooth', __name__)


@bluetooth_bp.route("/bluetooth/scan", methods=['GET'])
def bluetooth_scan() -> ResponseReturnValue:
    """扫描蓝牙设备（通过 device_agent 服务）。"""
    try:
        timeout = request.args.get('timeout', 5.0, type=float)
        log.info(f"===== [Bluetooth Scan] timeout={timeout}")
        devices = bluetooth_mgr.scan_devices_sync(timeout)
        return _ok(devices)
    except Exception as e:
        log.error(f"[Bluetooth] Scan error: {e}")
        return _err(f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/device", methods=['GET'])
def bluetooth_get_device() -> ResponseReturnValue:
    """获取指定蓝牙设备信息（通过 device_agent 服务）。"""
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
def bluetooth_connect() -> ResponseReturnValue:
    """连接蓝牙设备（通过 device_agent 服务）。"""
    try:
        args: Dict[str, Any] = read_json_from_request()
        log.info(f"===== [Bluetooth Connect] {json.dumps(args)}")
        address = args.get('address')
        if not address:
            return _err("address is required")
        result = bluetooth_mgr.connect_device_sync(address)
        if isinstance(result, dict) and 'code' in result:
            return result
        return _ok(result)
    except Exception as e:
        log.error(f"[Bluetooth] Connect error: {e}")
        return _err(f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/disconnect", methods=['POST'])
def bluetooth_disconnect() -> ResponseReturnValue:
    """断开蓝牙设备（通过 device_agent 服务）。"""
    try:
        args: Dict[str, Any] = read_json_from_request()
        log.info(f"===== [Bluetooth Disconnect] {json.dumps(args)}")
        address = args.get('address')
        if not address:
            return _err("address is required")
        result = bluetooth_mgr.disconnect_device_sync(address)
        if isinstance(result, dict) and 'code' in result:
            return result
        return _ok(result)
    except Exception as e:
        log.error(f"[Bluetooth] Disconnect error: {e}")
        return _err(f'error: {str(e)}')


@bluetooth_bp.route("/bluetooth/paired", methods=['GET'])
def bluetooth_get_paired() -> ResponseReturnValue:
    """获取系统已配对的蓝牙设备列表（通过 device_agent 服务）。"""
    try:
        log.info("===== [Bluetooth Get Paired Devices]")
        devices = bluetooth_mgr.get_paired_devices()
        return _ok(devices)
    except Exception as e:
        log.error(f"[Bluetooth] Get paired devices error: {e}")
        return _err(f'error: {str(e)}')
