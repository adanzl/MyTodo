'''
Agent 设备管理路由
通过调用 device_agent 服务接口实现
'''
from flask import Blueprint, request
from core.log_config import root_logger
from core.services.agent_mgr import agent_mgr
from core.utils import _ok, _err

log = root_logger()
agent_bp = Blueprint('agent', __name__)


@agent_bp.route("/agent/heartbeat", methods=['POST'])
def agent_heartbeat():
    """
    心跳接口（用于设备注册和心跳更新）
    """
    try:
        args = request.get_json() or {}
        address = args.get('address')
        if not address:
            return _err("address is required")

        name = args.get('name')
        actions = args.get('actions')

        log.debug(f"===== [Agent Heartbeat] address={address}, name={name}, actions={actions}")
        agent_mgr.handle_heartbeat(address=address, name=name, actions=actions)
        return _ok()
    except Exception as e:
        log.error(f"[Agent] Heartbeat error: {e}")
        return _err(f'error: {str(e)}')
