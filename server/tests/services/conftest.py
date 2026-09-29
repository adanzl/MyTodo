"""共享测试 fixture。"""

import pytest

from core.chat import chat_request_store


@pytest.fixture
def memory_rds(monkeypatch):
    """隔离 chat 请求共享存储，并强制走进程内锁路径（不触达真实 Redis Lua）。"""
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
    monkeypatch.setattr(
        chat_request_store.rds_mgr,
        "eval_lua",
        lambda *_a, **_k: None,
    )
    return store
