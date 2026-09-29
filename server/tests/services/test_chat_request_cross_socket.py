"""新 Socket / 新 ClientContext 仍应通过持久 phase 去重。"""

from unittest.mock import MagicMock

import pytest

from core.chat import chat_request_store
from core.chat.chat_mgr import ChatMgr, ClientContext


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


def test_second_socket_ignores_duplicate_text_when_store_phase_is_ai(
    memory_rds,
):
    chat_request_store.set_phase("leo", "req-x", "ai")

    socketio = MagicMock()
    ctx = ClientContext("sid-new", socketio)
    ctx.ai.user = "leo"
    ctx.ai.stream_msg = MagicMock()

    mgr = ChatMgr()
    mgr.clients = {"sid-new": ctx}
    mgr.socketio = socketio

    mgr.handle_text(
        "sid-new",
        {
            "chatType": "chat_ai",
            "content": "hello again",
            "clientRequestId": "req-x",
        },
    )

    ctx.ai.stream_msg.assert_not_called()
    accepted = [c for c in socketio.emit.call_args_list if c[0][0] == "msgAccepted"]
    assert len(accepted) == 1
