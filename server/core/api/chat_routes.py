"""Chat 路由模块（chat_bp）。

Dify 对话数据对外暴露的 HTTP 接口：
- `GET /chat/messages`：拉取某个会话的消息列表；
- `GET /chat/conversations`：拉取某个用户的会话列表；
- `GET /chat/export`：按日期范围导出某个会话的记录（CSV 附件）。

业务逻辑在 `ChatMgr`（`core/chat/chat_mgr.py`），本模块只是薄适配层：解析请求
参数、调用 mgr、把返回值交给 Flask（`_ok/_err` dict 会被序列化成 JSON，
导出成功时 mgr 直接返回 `flask.Response` 文件流）。

由 `core/__init__.py` 以 `url_prefix='/chat'` 注册，再经 `main.py` 的
`DispatcherMiddleware({'/api': app})` 补上前缀，最终对外为 `/api/chat/*`。
"""

from __future__ import annotations

import json

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from core.chat.chat_mgr import chat_mgr
from core.config import app_logger
from core.utils import _err

log = app_logger
chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/messages', methods=['GET'])
def chat_messages() -> ResponseReturnValue:
    """获取指定会话的消息列表。

    Query:
        conversation_id: 必填，Dify 会话 id。
        user: 必填，Dify 侧用户标识（同时决定使用哪个 Dify 应用）。
        limit: 可选，每页条数。
        first_id: 可选，本页最旧一条的 id，用于往更早翻页。

    返回 `{"code":0,"data":{limit,has_more,data:[...]}}`，`data` 内按时间从旧到新。
    注意：取数失败时底层会返回 `None`，此处仍是 `code:0` + `data:null`
    （既有行为，详见 `ChatMgr.get_messages`）。
    """
    try:
        log.info("=> [Chat Messages] " + json.dumps(request.args, ensure_ascii=False))
        return chat_mgr.get_messages(
            request.args.get('conversation_id'),
            request.args.get('limit'),
            request.args.get('user'),
            request.args.get('first_id'),
        )
    except Exception as e:
        log.error(e)
        return _err(str(e))


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
        log.info("=> [Chat Conversations] " + json.dumps(request.args, ensure_ascii=False))
        return chat_mgr.get_conversations(
            request.args.get('user'),
            request.args.get('limit'),
            request.args.get('last_id'),
        )
    except Exception as e:
        log.error(e)
        return _err(str(e))


@chat_bp.route('/export', methods=['GET'])
def chat_export() -> ResponseReturnValue:
    """按日期范围导出会话消息，返回 CSV 附件。

    Query:
        conversation_id: 必填，Dify 会话 id。
        user: 必填，Dify 侧用户标识（同时决定使用哪个 Dify 应用）。
        start: 可选，起始日期 `YYYY-MM-DD`（含当天 00:00:00）。
        end: 可选，结束日期 `YYYY-MM-DD`（含当天 23:59:59）。

    日期留空表示不限。时区按服务端本地时区解释（线上为 Asia/Shanghai）。

    参数校验、取数、过滤、CSV 生成与响应头拼装都在 `chat_mgr.export_messages`
    里完成，本路由只把 query 原样转过去 —— 放在服务端做的原因：Dify 的
    `/messages` 只支持游标分页且不返回总数，前端要自己翻页、把整段会话缓存在
    内存里再过滤；这里一次做完更省往返，日期口径也只有一处。

    注意返回体是文件流而非 `{code,msg,data}`：失败时仍是统一格式的 JSON，
    与 `Content-Type: text/csv` 区分，前端据此判断是文件还是错误。
    """
    try:
        log.info("=> [Chat Export] " + json.dumps(request.args, ensure_ascii=False))
        return chat_mgr.export_messages(
            request.args.get('conversation_id'),
            request.args.get('user'),
            start=request.args.get('start'),
            end=request.args.get('end'),
        )
    except Exception as e:
        log.error(e)
        return _err(str(e))
