"""queryChatRequest：重连后按 clientRequestId 查询持久 phase。"""

from unittest.mock import MagicMock

import pytest

from core.chat import chat_request_store
from core.chat.chat_mgr import ClientContext


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


def test_query_request_phases_reads_cross_socket_store(memory_rds):
    chat_request_store.set_phase("leo", "req-q1", "done")
    chat_request_store.set_phase("leo", "req-q2", "ai")

    ctx = ClientContext("sid-1", MagicMock())
    ctx.ai.user = "leo"

    items = ctx.query_request_phases(["req-q1", "req-q2", "req-missing"])
    by_id = {x["clientRequestId"]: x["phase"] for x in items}

    assert by_id["req-q1"] == "done"
    assert by_id["req-q2"] == "ai"
    assert by_id["req-missing"] is None
