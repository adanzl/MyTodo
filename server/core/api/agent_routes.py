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


def _get_client_ip():
    """获取客户端 IP 地址"""
    # 优先检查代理头
    if request.headers.get('X-Forwarded-For'):
        # X-Forwarded-For 可能包含多个 IP，取第一个
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
    else:
        ip = request.remote_addr
    return ip


@agent_bp.route("/agent/heartbeat", methods=['POST'])
def agent_heartbeat():
    """
    心跳接口（用于设备注册和心跳更新）
    """
    try:
        args = request.get_json() or {}
        address = args.get('address')
        client_ip = _get_client_ip()

        # 如果没有提供 address，使用客户端 IP + 默认端口
        if not address:
            return _err("address is required")

        name = args.get('name')
        actions = args.get('actions')

        log.debug(f"===== [Agent Heartbeat] client_ip={client_ip}, address={address}, name={name}, actions={actions}")
        agent_mgr.handle_heartbeat(client_ip=client_ip, address=address, name=name, actions=actions)
        return _ok()
    except Exception as e:
        log.error(f"[Agent] Heartbeat error: {e}")
        return _err(f'error: {str(e)}')


@agent_bp.route("/agent/event", methods=['POST'])
def agent_event():
    """
    触发事件接口
    """
    try:
        args = request.get_json() or {}
        client_ip = _get_client_ip()
        log.info(f"===== [Agent Event] client_ip={client_ip}, {args}")

        _key = args.get('key')
        _value = args.get('value')
        _action = args.get('action')

        code, msg = agent_mgr.handle_event(client_ip=client_ip, key=_key, value=_value, action=_action)
        if code == 0:
            return _ok()
        else:
            return _err(msg)
    except KeyError:
        return _err("agent not found")
    except Exception as e:
        log.error(f"[Agent] Trigger event error: {e}")
        return _err(f'error: {str(e)}')
