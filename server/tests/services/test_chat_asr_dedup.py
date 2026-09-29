"""同一 clientRequestId 的重复/迟到 ASR 结果不得二次进入 AI。"""

from unittest.mock import MagicMock

from core.chat import chat_request_store
from core.chat.chat_mgr import ClientContext

USER = "asr-dedup-user"


def _asr_phase(user: str, rid: str) -> None:
    chat_request_store.try_transition(user, rid, None, "accepted")
    chat_request_store.set_phase(user, rid, "asr")


def test_duplicate_asr_result_calls_ai_once(memory_rds):
    socketio = MagicMock()
    ctx = ClientContext("sid-1", socketio)
    ctx.ai.user = USER
    ctx.ai.stream_msg = MagicMock()

    _asr_phase(USER, "req-v1")
    ctx.on_asr_result("第一次", "req-v1")
    ctx.on_asr_result("第二次", "req-v1")

    ctx.ai.stream_msg.assert_called_once_with("第一次", client_request_id="req-v1")
    asr_emits = [c for c in socketio.emit.call_args_list if c[0][0] == "msgAsr"]
    assert len(asr_emits) == 1
    assert chat_request_store.get_phase(USER, "req-v1") == "ai"


def test_late_asr_after_cancel_does_not_restart_ai(memory_rds):
    socketio = MagicMock()
    ctx = ClientContext("sid-1", socketio)
    ctx.ai.user = USER
    ctx.ai.stream_msg = MagicMock()

    chat_request_store.set_phase(USER, "req-v1", "cancelled")

    ctx.on_asr_result("迟到识别", "req-v1")

    ctx.ai.stream_msg.assert_not_called()
    assert chat_request_store.get_phase(USER, "req-v1") == "cancelled"


def test_late_asr_after_done_does_not_emit_or_call_ai(memory_rds):
    socketio = MagicMock()
    ctx = ClientContext("sid-1", socketio)
    ctx.ai.user = USER
    ctx.ai.stream_msg = MagicMock()

    chat_request_store.set_phase(USER, "req-v1", "done")

    ctx.on_asr_result("迟到识别", "req-v1")

    ctx.ai.stream_msg.assert_not_called()
    assert not any(c[0][0] == "msgAsr" for c in socketio.emit.call_args_list)
