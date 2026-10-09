"""Chat 路由模块（chat_bp）。

Dify 对话数据的 HTTP 代理层：
- `GET /chat/messages`：拉取某个会话的消息列表；
- `GET /chat/conversations`：拉取某个用户的会话列表。

由 `core/__init__.py` 以 `url_prefix='/chat'` 注册，再经 `main.py` 的
`DispatcherMiddleware({'/api': app})` 补上前缀，最终对外为 `/api/chat/*`。
"""

from __future__ import annotations

import json

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from core.ai.ai_local import AILocal
from core.config import app_logger
from core.utils import _err, _ok

log = app_logger
chat_bp = Blueprint('chat', __name__)

# Dify 单页上限；超出会被上游忽略或报错，这里主动收敛
MAX_LIMIT = 100
DEFAULT_LIMIT = 20


def _parse_limit(raw) -> int:
    """把 limit 收敛到 [1, MAX_LIMIT]，非法值回落到默认值。"""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    return max(1, min(value, MAX_LIMIT))


@chat_bp.route('/messages', methods=['GET'])
def chat_messages() -> ResponseReturnValue:
    """获取指定会话的消息列表。

    Query:
        conversation_id: 必填，Dify 会话 id。
        user: 必填，Dify 侧用户标识（同时决定使用哪个 Dify 应用）。
        limit: 可选，每页条数。
        first_id: 可选，本页最旧一条的 id，用于往更早翻页。

    返回 `{"code":0,"data":{limit,has_more,data:[...]}}`，`data` 内按时间从旧到新。
    注意：取数失败时 `AILocal.get_chat_messages` 会返回 `None`（见该方法的说明），
    此处不做额外包装以保持既有行为不变。
    """
    try:
        log.info("=> [Chat Messages] " + json.dumps(request.args, ensure_ascii=False))
        c_id = request.args.get('conversation_id')
        limit = request.args.get('limit')
        first_id = request.args.get('first_id')
        user = request.args.get('user')
        return _ok(AILocal.get_chat_messages(c_id, limit, user, first_id))
    except Exception as e:
        log.error(e)
        return _err('error' + str(e))


@chat_bp.route('/conversations', methods=['GET'])
def chat_conversations() -> ResponseReturnValue:
    """获取指定用户的 Dify 会话列表（按 updated_at 倒序）。

    Query:
        user: 必填，Dify 侧用户标识（同时决定使用哪个 Dify 应用）。
        limit: 可选，默认 20，最大 100。
        last_id: 可选，上一页最后一条会话 id，用于往更早翻页。

    与 `/messages` 不同：取数失败会返回 `code:-1` 并把上游错误透出，
    避免前端把「请求失败」误判成「没有会话」。
    """
    try:
        user = (request.args.get('user') or '').strip()
        if not user:
            return _err('user is required')
        log.info("=> [Chat Conversations] " + json.dumps(request.args, ensure_ascii=False))
        limit = _parse_limit(request.args.get('limit'))
        last_id = (request.args.get('last_id') or '').strip() or None
        return _ok(AILocal.get_conversations(user, limit, last_id))
    except Exception as e:
        log.error(e)
        return _err(str(e))
