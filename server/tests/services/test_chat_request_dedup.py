"""clientRequestId 去重：重复 text 不触发第二次 AI。"""

from unittest.mock import MagicMock

import pytest

from core.chat import chat_request_store
from core.chat.chat_mgr import ClientContext, ChatMgr


@pytest.fixture
def memory_rds(monkeypatch):
    store: dict[str, str] = {}

    monkeypatch.setattr(
        chat_request_store.rds_mgr,
        "get_str",
        lambda key: store.get(key, ""),
    )
    monkeypatch.setattr(
        chat_request_store.rds_mgr,
        "setex",
        lambda key, _ttl, value: store.__setitem__(key, value) or True,
    )
    return store


def test_duplicate_text_emits_accepted_but_not_second_ai(memory_rds):
    socketio = MagicMock()
    ctx = ClientContext("sid-1", socketio)
    ctx.ai.user = "test-user"
    ctx.ai.stream_msg = MagicMock()

    mgr = ChatMgr()
    mgr.clients = {"sid-1": ctx}
    mgr.socketio = socketio

    data = {
        "chatType": "chat_ai",
        "content": "hello",
        "clientRequestId": "req-dup-1",
    }
    mgr.handle_text("sid-1", data)
    mgr.handle_text("sid-1", data)

    ctx.ai.stream_msg.assert_called_once_with("hello", client_request_id="req-dup-1")
    accepted = [
        c
        for c in socketio.emit.call_args_list
        if c[0][0] == "msgAccepted"
    ]
    assert len(accepted) == 2
    assert accepted[0][0][1]["clientRequestId"] == "req-dup-1"
