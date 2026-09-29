"""clientRequestId 须绑定到单次 AI/ASR 请求，不能随 ClientContext 共享字段漂移。"""

from unittest.mock import MagicMock

from core.chat.chat_mgr import ClientContext


def test_on_ai_msg_emits_bound_request_id_not_context_field():
    socketio = MagicMock()
    ctx = ClientContext("sid-1", socketio)

    ctx.on_ai_msg("hi", "msg-1", 0, client_request_id="req-old")
    ctx.asr_session_request_id = "req-new"
    ctx.on_ai_msg("bye", "msg-2", 0, client_request_id="req-old")

    calls = socketio.emit.call_args_list
    assert calls[0][0][1]["clientRequestId"] == "req-old"
    assert calls[1][0][1]["clientRequestId"] == "req-old"


def test_on_asr_result_uses_callback_request_id():
    socketio = MagicMock()
    ctx = ClientContext("sid-1", socketio)
    ctx.ai.stream_msg = MagicMock()

    ctx.on_asr_result("你好", "voice-req-1")

    socketio.emit.assert_called_with(
        "msgAsr",
        {"content": "你好", "clientRequestId": "voice-req-1"},
        room="sid-1",
    )
    ctx.ai.stream_msg.assert_called_once_with("你好", client_request_id="voice-req-1")
