"""A 识别超时/取消后 B 录音，A 的迟到 ASR 不应触发 B 的 AI。"""

from unittest.mock import MagicMock

from core.chat.asr_client import AsrClient, _AsrSession
from core.chat.chat_mgr import ClientContext


def test_late_asr_result_keeps_request_id_from_callback_not_overwritten_session():
    socketio = MagicMock()
    ctx = ClientContext("sid-1", socketio)
    ctx.ai.stream_msg = MagicMock()

    ctx.on_asr_result("来自A", "req-a")
    ctx.on_asr_result("来自B", "req-b")

    assert socketio.emit.call_args_list[0][0][1]["clientRequestId"] == "req-a"
    assert socketio.emit.call_args_list[1][0][1]["clientRequestId"] == "req-b"
    ctx.ai.stream_msg.assert_any_call("来自A", client_request_id="req-a")
    ctx.ai.stream_msg.assert_any_call("来自B", client_request_id="req-b")


def test_cancel_asr_then_new_session_accepts_result():
    results: list[tuple[str, str]] = []

    def on_result(text, rid=""):
        results.append((text, rid))

    asr = AsrClient(on_result, lambda _e: None)
    asr.sid = "sid-1"
    asr.begin_session("req-a")
    asr.cancel_session("req-a")
    asr.begin_session("req-b")
    asr._ws_generation = 1
    asr._ws_generation += 1
    gen = asr._ws_generation
    asr._sessions_by_generation[gen] = _AsrSession("req-b", gen)
    asr._session = asr._sessions_by_generation[gen]

    handler = asr._make_on_message(gen)
    handler(MagicMock(), '{"mode":"offline","text":"B识别"}')

    assert results == [("B识别", "req-b")]


def test_cancel_a_during_slow_stop_does_not_close_b_asr():
    ctx = ClientContext("sid-1", MagicMock())
    asr = ctx.asr
    asr.sid = "sid-1"
    asr._sessions_by_generation[1] = _AsrSession("req-a", 1)
    asr._sessions_by_generation[2] = _AsrSession("req-b", 2)
    asr._session = asr._sessions_by_generation[2]
    asr.ws = MagicMock()
    asr.is_running = True

    ctx.cancel_asr("req-a")

    assert asr._sessions_by_generation[1].cancelled is True
    assert asr._sessions_by_generation[2].cancelled is False
    assert asr.ws is not None
