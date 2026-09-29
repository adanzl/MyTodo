"""共享 phase 原子转换、失败重试与快照查询。"""

from unittest.mock import MagicMock

from core.chat import chat_request_store
from core.chat.chat_mgr import ChatMgr, ClientContext


def test_try_begin_ai_only_one_wins(memory_rds):
    user = "leo"
    rid = "req-atomic-1"
    chat_request_store.try_transition(user, rid, None, "accepted")

    ok_a = chat_request_store.try_transition(
        user, rid, frozenset({"accepted", "asr"}), "ai"
    )
    ok_b = chat_request_store.try_transition(
        user, rid, frozenset({"accepted", "asr"}), "ai"
    )
    assert ok_a is True
    assert ok_b is False


def test_query_reads_latest_phase_not_stale_local_cache(memory_rds):
    user = "leo"
    rid = "req-stale-1"
    chat_request_store.try_transition(user, rid, None, "accepted")
    chat_request_store.try_transition(
        user, rid, frozenset({"accepted", "asr"}), "ai"
    )

    ctx = ClientContext("sid-a", MagicMock())
    ctx.ai.user = user
    ctx._request_phase[rid] = "ai"

    chat_request_store.set_phase(user, rid, "done")

    items = ctx.query_request_phases([rid])
    assert items[0]["phase"] == "done"


def test_failed_phase_allows_retry_with_same_id(memory_rds):
    socketio = MagicMock()
    ctx = ClientContext("sid-1", socketio)
    ctx.ai.user = "u1"
    ctx.ai.stream_msg = MagicMock()

    mgr = ChatMgr()
    mgr.clients = {"sid-1": ctx}
    mgr.socketio = socketio

    rid = "req-fail-retry"
    chat_request_store.mark_failed("u1", rid, "boom")

    data = {
        "chatType": "chat_ai",
        "content": "again",
        "clientRequestId": rid,
    }
    mgr.handle_text("sid-1", data)

    ctx.ai.stream_msg.assert_called_once_with("again", client_request_id=rid)


def test_on_err_marks_failed(memory_rds):
    ctx = ClientContext("sid-1", MagicMock())
    ctx.ai.user = "u1"
    chat_request_store.try_transition("u1", "rid-e", None, "accepted")
    chat_request_store.try_transition(
        "u1", "rid-e", frozenset({"accepted", "asr"}), "ai"
    )

    ctx.on_err(RuntimeError("network"), "rid-e")

    assert chat_request_store.get_phase("u1", "rid-e") == "failed"


def test_retry_from_failed_clears_reply_snapshot(memory_rds):
    user = "leo"
    rid = "rid-retry-snap"
    chat_request_store.try_transition(user, rid, None, "ai")
    chat_request_store.append_reply_text(user, rid, "old partial")
    chat_request_store.mark_failed(user, rid, "err")
    assert chat_request_store.try_transition(
        user, rid, chat_request_store.RETRYABLE, "accepted"
    )
    chat_request_store.append_reply_text(user, rid, "new answer", attempt=1)
    ctx = ClientContext("sid", MagicMock())
    ctx.ai.user = user
    items = ctx.query_request_phases([rid])
    assert items[0]["replyText"] == "new answer"
    assert items[0].get("attempt") == 1


def test_stale_attempt_ai_msg_does_not_mutate_store_or_emit(memory_rds):
    user = "leo"
    rid = "rid-stale-chunk"
    ctx = ClientContext("sid", MagicMock())
    ctx.ai.user = user
    socketio = ctx.socketio

    chat_request_store.try_transition(user, rid, None, "accepted")
    chat_request_store.try_transition(
        user, rid, frozenset({"accepted", "asr"}), "ai"
    )
    chat_request_store.mark_failed(user, rid, "boom", attempt=0)
    chat_request_store.try_transition(
        user, rid, chat_request_store.RETRYABLE, "accepted"
    )
    chat_request_store.try_transition(
        user, rid, frozenset({"accepted", "asr"}), "ai"
    )
    chat_request_store.append_reply_text(user, rid, "new", attempt=1)

    ctx.on_ai_msg("stale", "m1", 0, client_request_id=rid, attempt=0)

    socketio.emit.assert_not_called()
    rec = chat_request_store.get_record(user, rid)
    assert rec["reply_text"] == "new"


def test_stale_attempt_error_does_not_mark_failed(memory_rds):
    user = "leo"
    rid = "rid-stale-err"
    ctx = ClientContext("sid", MagicMock())
    ctx.ai.user = user

    chat_request_store.try_transition(user, rid, None, "accepted")
    chat_request_store.try_transition(
        user, rid, frozenset({"accepted", "asr"}), "ai"
    )
    chat_request_store.mark_failed(user, rid, "first", attempt=0)
    chat_request_store.try_transition(
        user, rid, chat_request_store.RETRYABLE, "accepted"
    )
    chat_request_store.try_transition(
        user, rid, frozenset({"accepted", "asr"}), "ai"
    )

    ctx.on_err(RuntimeError("late"), rid, attempt=0)

    assert chat_request_store.get_phase(user, rid) == "ai"
    ctx.socketio.emit.assert_not_called()


def test_reply_snapshot_in_query(memory_rds):
    user = "leo"
    rid = "rid-reply"
    chat_request_store.try_transition(user, rid, None, "ai")
    chat_request_store.append_reply_text(user, rid, "你好")
    chat_request_store.set_phase(user, rid, "done")

    ctx = ClientContext("sid", MagicMock())
    ctx.ai.user = user
    items = ctx.query_request_phases([rid])
    assert items[0]["phase"] == "done"
    assert items[0]["replyText"] == "你好"
