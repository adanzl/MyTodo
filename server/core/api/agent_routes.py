'''
Agent 设备管理路由
通过调用 device_agent 服务接口实现
'''
import json
from flask import Blueprint, request
from core.log_config import root_logger
from core.device.agent import DeviceAgent
from core.utils import _ok, _err

log = root_logger()
agent_bp = Blueprint('agent', __name__)
device_agent = DeviceAgent()


@agent_bp.route("/agent/paired", methods=['GET'])
def agent_get_paired():
    """
    获取已配对的设备列表（通过 device_agent 服务）
    """
    try:
        log.info("===== [Agent Get Paired Devices]")
        result = device_agent.bluetooth_get_paired()
        if result.get("code") == 0:
            return _ok(result.get("data"))
        else:
            return _err(result.get("msg", "获取已配对设备失败"))
    except Exception as e:
        log.error(f"[Agent] Get paired devices error: {e}")
        return _err(f'error: {str(e)}')


@agent_bp.route("/agent/scan", methods=['GET'])
def agent_scan():
    """
    扫描设备（通过 device_agent 服务）
    """
    try:
        timeout = request.args.get('timeout', 5.0, type=float)
        log.info(f"===== [Agent Scan] timeout={timeout}")
        result = device_agent.bluetooth_scan(timeout)
        if result.get("code") == 0:
            return _ok(result.get("data"))
        else:
            return _err(result.get("msg", "扫描设备失败"))
    except Exception as e:
        log.error(f"[Agent] Scan error: {e}")
        return _err(f'error: {str(e)}')


@agent_bp.route("/agent/connect", methods=['POST'])
def agent_connect():
    """
    连接设备（通过 device_agent 服务）
    """
    try:
        args = request.get_json()
        log.info("===== [Agent Connect] " + json.dumps(args))
        address = args.get('address')
        if not address:
            return _err("address is required")
        result = device_agent.bluetooth_connect(address)
        if result.get("code") == 0:
            return _ok(result.get("data"))
        else:
            return _err(result.get("msg", "连接设备失败"))
    except Exception as e:
        log.error(f"[Agent] Connect error: {e}")
        return _err(f'error: {str(e)}')


@agent_bp.route("/agent/play", methods=['POST'])
def agent_play():
    """
    播放媒体文件（通过 device_agent 服务）
    """
    try:
        args = request.get_json()
        log.info("===== [Agent Play] " + json.dumps(args))
        file_path = args.get('file_path') or args.get('url')
        if not file_path:
            return _err("file_path or url is required")
        
        code, msg = device_agent.play(file_path)
        if code == 0:
            return _ok()
        else:
            return _err(msg)
    except Exception as e:
        log.error(f"[Agent] Play error: {e}")
        return _err(f'error: {str(e)}')


@agent_bp.route("/agent/stop", methods=['POST'])
def agent_stop():
    """
    停止播放（通过 device_agent 服务）
    """
    try:
        log.info("===== [Agent Stop]")
        code, msg = device_agent.stop()
        if code == 0:
            return _ok()
        else:
            return _err(msg)
    except Exception as e:
        log.error(f"[Agent] Stop error: {e}")
        return _err(f'error: {str(e)}')


@agent_bp.route("/agent/heartbeat", methods=['GET'])
def agent_heartbeat():
    """
    心跳检测接口（用于检查 agent 服务是否可用）
    """
    try:
        log.debug("===== [Agent Heartbeat]")
        return _ok({"status": "ok"})
    except Exception as e:
        log.error(f"[Agent] Heartbeat error: {e}")
        return _err(f'error: {str(e)}')
