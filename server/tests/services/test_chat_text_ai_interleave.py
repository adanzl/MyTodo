"""text AI 交错：同一 clientRequestId 在 stream 阻塞期间不得二次 stream_msg。"""

from unittest.mock import MagicMock

from core.chat import chat_request_store
from core.chat.chat_mgr import ChatMgr, ClientContext


def test_duplicate_text_while_stream_in_progress_does_not_call_ai_twice(
    memory_rds,
):
    socketio = MagicMock()
    ctx = ClientContext("sid-1", socketio)
    ctx.ai.user = "interleave-user"
    mgr = ChatMgr()
    mgr.clients = {"sid-1": ctx}
    mgr.socketio = socketio

    data = {
        "chatType": "chat_ai",
        "content": "hello",
        "clientRequestId": "req-same-1",
    }
    nested = {"done": False}

    def blocking_stream(content, client_request_id=""):
        if not nested["done"]:
            nested["done"] = True
            mgr.handle_text("sid-1", data)

    ctx.ai.stream_msg = MagicMock(side_effect=blocking_stream)

    mgr.handle_text("sid-1", data)

    ctx.ai.stream_msg.assert_called_once_with("hello", client_request_id="req-same-1")
    assert chat_request_store.get_phase("interleave-user", "req-same-1") == "ai"


def test_mark_request_done_does_not_reopen_ai_phase(memory_rds):
    ctx = ClientContext("sid-1", MagicMock())
    ctx.ai.user = "u-done"
    chat_request_store.set_phase(ctx.ai.user, "req-1", "done")
    ctx.mark_request_done("req-1")
    assert chat_request_store.get_phase(ctx.ai.user, "req-1") == "done"
