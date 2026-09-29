import uuid

import pytest

from core.chat import chat_request_store


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


def test_set_and_get_phase_roundtrip(memory_rds):
    rid = f"rid-{uuid.uuid4().hex}"
    user = f"user-{uuid.uuid4().hex[:8]}"
    chat_request_store.set_phase(user, rid, "accepted")
    assert chat_request_store.get_phase(user, rid) == "accepted"
    chat_request_store.set_phase(user, rid, "ai")
    assert chat_request_store.get_phase(user, rid) == "ai"


def test_try_transition_rejects_double_create(memory_rds):
    user = "u"
    rid = "r1"
    assert chat_request_store.try_transition(user, rid, None, "accepted") is True
    assert chat_request_store.try_transition(user, rid, None, "accepted") is False
