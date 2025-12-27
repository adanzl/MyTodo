'''
Agent 设备管理路由
通过调用 device_agent 服务接口实现
'''
import time

from flask import Blueprint, request

from core.log_config import root_logger
from core.services.agent_mgr import agent_mgr
from core.utils import _err, _ok, read_json_from_request

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
        args = read_json_from_request()
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
        args = read_json_from_request()
        client_ip = _get_client_ip()
        log.info(f"===== [Agent Event] client_ip={client_ip}, {args}")

        _key = args.get('key')
        _value = args.get('value')
        _action = args.get('action')

        code, msg = agent_mgr.handle_event(client_ip=client_ip, key=_key, value=_value, action=_action)
        if code == 0:
            return _ok()
        else:
            log.error(f"[Agent] Trigger event error: {msg}")
            return _err(msg)
    except KeyError:
        return _err("agent not found")
    except Exception as e:
        log.error(f"[Agent] Trigger event error: {e}")
        return _err(f'error: {str(e)}')


@agent_bp.route("/agent/list", methods=['GET'])
def agent_list():
    """
    获取所有agent设备列表
    返回所有已注册设备的详细信息
    """
    try:
        devices = agent_mgr.get_all_agents()
        # 将字典转换为列表，包含详细信息

        current_time = time.time()
        device_list = []
        for address, device_info in devices.items():
            device_data = {
                'address': device_info.get('address', address),
                'name': device_info.get('name', address),
                'agent_id': device_info.get('agent_id', ''),
                'actions': device_info.get('actions', []),
                'register_time': device_info.get('register_time', 0),
                'heartbeat_time': device_info.get('heartbeat_time', 0),
                'last_heartbeat_ago': int(current_time - device_info.get('heartbeat_time', 0)) if device_info.get('heartbeat_time', 0) > 0 else 0,
                'is_online': (current_time - device_info.get('heartbeat_time', 0)) < 30 if device_info.get('heartbeat_time', 0) > 0 else False
            }
            device_list.append(device_data)
        return _ok(device_list)
    except Exception as e:
        log.error(f"[Agent] List error: {e}")
        return _err(f'error: {str(e)}')


@agent_bp.route("/agent/mock", methods=['POST'])
def agent_mock():
    """
    Mock接口，用于模拟设备操作
    参数: agent_id, action, key, value
    """
    try:
        args = read_json_from_request()
        log.info(f"===== [Agent Mock] {args}")
        agent_id = args.get('agent_id')
        action = args.get('action')
        key = args.get('key')
        value = args.get('value')

        if not agent_id or not action:
            return _err("agent_id and action are required")

        # 获取 agent 实例
        agent = agent_mgr.get_agent(agent_id)
        if not agent:
            return _err(f"agent not found: {agent_id}")

        # 调用 mock 方法
        result = agent.mock(action=action, key=key, value=value)
        
        if result.get("code") == 0:
            return _ok(result.get("data"))
        else:
            return _err(result.get("msg", "mock操作失败"))
    except Exception as e:
        log.error(f"[Agent] Mock error: {e}")
        return _err(f'error: {str(e)}')
