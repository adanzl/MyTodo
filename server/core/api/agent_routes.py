"""Agent 设备管理路由。

该模块提供与 DeviceAgent 相关的 HTTP 接口，包括：
- 设备心跳上报与注册
- 设备事件接收
- 设备列表查询
- 设备操作模拟（用于测试）

所有接口都通过 `core.services.agent_mgr` 与实际的 Agent 实例交互。
"""
import time
from typing import Any, Dict

from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from pydantic import BaseModel

from core.config import app_logger
from core.services.agent_mgr import agent_mgr
from core.tools.validation import parse_with_model
from core.utils import _err, _ok, read_json_from_request

log = app_logger
agent_bp = Blueprint('agent', __name__)

from core import limiter


class _AgentHeartbeatBody(BaseModel):
    address: str
    name: str | None = None
    actions: list[str] | None = None


class _AgentEventBody(BaseModel):
    key: str
    action: str
    value: Any | None = None


class _AgentMockBody(BaseModel):
    agent_id: str
    action: str
    key: str | None = None
    value: Any | None = None


def _get_client_ip() -> str:
    """获取请求的客户端 IP 地址。

    优先从 `X-Forwarded-For` 或 `X-Real-IP` HTTP 头中获取，
    以支持反向代理部署。

    Returns:
        str: 客户端 IP 地址。
    """
    # 优先检查代理头
    if request.headers.get('X-Forwarded-For'):
        # X-Forwarded-For 可能包含多个 IP，取第一个
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
    else:
        ip = request.remote_addr
    return ip or ''


@agent_bp.route("/agent/heartbeat", methods=['POST'])
def agent_heartbeat() -> ResponseReturnValue:
    """接收并处理 Agent 的心跳上报。

    用于设备注册和状态更新。客户端 IP 被用作 Agent 的唯一标识。

    JSON Body:
        address (str): Agent 的访问地址 (e.g., "192.168.1.10:8000")。
        name (str, optional): Agent 的可读名称。
        actions (list[str], optional): Agent 支持的操作列表。

    Returns:
        ResponseReturnValue: 成功时返回 code=0，失败时返回错误信息。
    """
    try:
        data: Dict[str, Any] = read_json_from_request()
        body, err = parse_with_model(_AgentHeartbeatBody, data, err_factory=_err)
        if err:
            return err

        client_ip = _get_client_ip()

        log.debug(
            f"===== [Agent Heartbeat] client_ip={client_ip}, address={body.address}, name={body.name}, actions={body.actions}"
        )
        agent_mgr.handle_heartbeat(client_ip=client_ip, address=body.address, name=body.name, actions=body.actions)
        return _ok()
    except Exception as e:
        log.error(f"[Agent] Heartbeat error: {e}")
        return _err(f'error: {str(e)}')


@limiter.limit("10 per minute; 50 per hour")
@agent_bp.route("/agent/event", methods=['POST'])
def agent_event() -> ResponseReturnValue:
    """接收并处理来自 Agent 的事件。

    例如，接收键盘事件并映射为播放控制指令。

    JSON Body:
        key (str): 事件的键。
        value (Any): 事件的值。
        action (str): 事件的动作类型。

    Returns:
        ResponseReturnValue: 成功时返回 code=0，失败时返回错误信息。
    """
    try:
        data: Dict[str, Any] = read_json_from_request()
        body, err = parse_with_model(_AgentEventBody, data, err_factory=_err)
        if err:
            return err

        client_ip = _get_client_ip()
        log.info(f"===== [Agent Event] client_ip={client_ip}, {data}")

        code, msg = agent_mgr.handle_event(client_ip=client_ip,
                                           key=body.key,
                                           value=str(body.value or ''),
                                           action=body.action)
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
def agent_list() -> ResponseReturnValue:
    """获取所有 Agent 设备列表。

    返回所有已注册设备的详细信息，包括在线状态和心跳时间。

    Returns:
        ResponseReturnValue: 包含设备列表的成功响应，或错误信息。
    """
    try:
        devices = agent_mgr.get_all_agents()
        current_time = time.time()
        device_list = []
        for address, device_info in devices.items():
            heartbeat_time = device_info.get('heartbeat_time', 0)
            device_data = {
                'address': device_info.get('address', address),
                'name': device_info.get('name', address),
                'agent_id': device_info.get('agent_id', ''),
                'actions': device_info.get('actions', []),
                'register_time': device_info.get('register_time', 0),
                'heartbeat_time': heartbeat_time,
                'last_heartbeat_ago': int(current_time - heartbeat_time) if heartbeat_time > 0 else -1,
                'is_online': (current_time - heartbeat_time) < 30 if heartbeat_time > 0 else False
            }
            device_list.append(device_data)
        return _ok(device_list)
    except Exception as e:
        log.error(f"[Agent] List error: {e}")
        return _err(f'error: {str(e)}')


@agent_bp.route("/agent/mock", methods=['POST'])
def agent_mock() -> ResponseReturnValue:
    """模拟 Agent 设备操作接口，用于测试或调试。

    JSON Body:
        agent_id (str): 目标 Agent 的唯一 ID。
        action (str): 要执行的动作名称。
        key (str, optional): 动作的 key 参数。
        value (Any, optional): 动作的 value 参数。

    Returns:
        ResponseReturnValue: 成功时返回 mock 结果，失败时返回错误信息。

    Raises:
        KeyError: 当 `agent_id` 未注册时，由 `agent_mgr.get_agent` 抛出。
    """
    try:
        data: Dict[str, Any] = read_json_from_request()
        body, err = parse_with_model(_AgentMockBody, data, err_factory=_err)
        if err:
            return err

        log.info(f"===== [Agent Mock] {data}")

        agent = agent_mgr.get_agent(body.agent_id)
        if not agent:
            return _err(f"agent not found: {body.agent_id}")

        result = agent.mock(action=body.action, key=body.key, value=body.value)

        if result.get("code") == 0:
            return _ok(result.get("data"))
        else:
            return _err(result.get("msg", "mock操作失败"))
    except Exception as e:
        log.error(f"[Agent] Mock error: {e}")
        return _err(f'error: {str(e)}')
