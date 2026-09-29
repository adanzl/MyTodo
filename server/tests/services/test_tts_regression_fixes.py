"""复测 TTS 相关修复：on_error 上报、任务超时/总字数、Redis 缓存回放。"""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from core.chat.chat_mgr import ChatMgr, ClientContext
from core.services.tools.tts_mgr import (
    TTSMgr,
    TTS_DATA_IDLE_TIMEOUT,
    TASK_COMPLETION_TIMEOUT,
    count_text_chars,
)
from core.tts.tts_client import TTSClient


def test_tts_client_on_error_invokes_on_err_once():
    errors: list[Exception] = []
    tts = TTSClient(on_err=errors.append)
    tts.on_error("synthesis failed")
    tts.on_error("synthesis failed again")
    assert len(errors) == 1
    assert "synthesis failed" in str(errors[0])


def test_tts_client_stream_msg_updates_role_for_redis_key():
    with patch("core.tts.tts_client.SpeechSynthesizer") as synth_cls:
        synth_cls.return_value = MagicMock()
        tts = TTSClient()
        tts.stream_msg("你好", role="custom_voice", id="msg-42")
        assert tts.role == "custom_voice"

        with patch("core.chat.tts_cache.rds_mgr") as rds:
            rds.set = MagicMock(return_value=True)
            rds.setex = MagicMock(return_value=True)
            rds.append_value = MagicMock()
            tts.start_immediate_cache("msg-42", "hello", "custom_voice", 1.0)
            tts.on_data(b"chunk")
            assert rds.append_value.call_count == 1
            assert rds.append_value.call_args[0][1] == b"chunk"


def test_one_shot_tts_keeps_synthesizer_reference_for_cancel():
    tts = TTSClient()
    synth = MagicMock()

    def _call(_text):
        assert tts.synthesizer is synth

    synth.call.side_effect = _call
    with patch("core.tts.tts_client.SpeechSynthesizer", return_value=synth):
        tts.process_msg("需要中止的朗读", role="longwan_v3", id="msg-cancel")

    tts.streaming_cancel()
    synth.streaming_cancel.assert_called_once()


def test_auto_tts_keeps_first_chunk_tail_and_full_text():
    socketio = MagicMock()
    ctx = ClientContext("sid-auto-tts", socketio)
    ctx.autoTTS = True
    ctx.tts = MagicMock()
    ctx.tts.role = "longwan_v3"
    ctx.tts.speed = 1.1

    ctx.on_ai_msg("你好。后面", "msg-auto-1", type=0)

    ctx.tts.start_deferred_cache.assert_called_once_with("msg-auto-1")
    ctx.tts.stream_msg.assert_called_once_with(text="你好。", id="msg-auto-1")
    assert ctx._tts_phrase_buffer.full_text == "你好。后面"

    ctx.on_ai_msg("", "msg-auto-1", type=1)

    assert ctx.tts.stream_msg.call_args_list[-1].kwargs == {
        "text": "后面",
        "id": "msg-auto-1",
    }
    ctx.tts.prepare_deferred_cache.assert_called_once_with(
        "你好。后面",
        role="longwan_v3",
        speed=1.1,
    )
    ctx.tts.stream_complete.assert_called_once()


def test_tts_client_deferred_cache_commits_only_after_sdk_complete():
    tts = TTSClient()
    tts.start_deferred_cache("msg-deferred")
    tts.on_data(b"audio")
    tts.prepare_deferred_cache("完整文本", role="longwan_v3", speed=1.0)

    with patch("core.chat.tts_cache.begin_session") as begin, patch(
        "core.chat.tts_cache.finalize_session"
    ) as finalize, patch("core.tts.tts_client.rds_mgr.append_value") as append:
        begin.return_value = {"audio_key": "audio", "meta_key": "meta", "text_hash": "hash"}
        assert begin.call_count == 0

        tts.on_complete()

        begin.assert_called_once()
        append.assert_called_once_with("audio", b"audio")
        finalize.assert_called_once_with(begin.return_value)


def test_tts_end_clears_manual_request_id_after_emitting_it():
    socketio = MagicMock()
    ctx = ClientContext("sid-tts-id", socketio)
    ctx._tts_emit_request_id = "tts-123"

    ctx.on_tts_msg("done", 1)

    emit = [c for c in socketio.emit.call_args_list if c[0][0] == "endAudio"][-1]
    assert emit[0][1]["ttsRequestId"] == "tts-123"
    assert ctx._tts_emit_request_id is None


def test_tts_mgr_sets_total_chars_with_count_text_chars_rule(tts_mgr: TTSMgr, tmp_path):
    text = "你好ab"
    expected = count_text_chars(text)
    assert expected == 6

    code, _, task_id = tts_mgr.create_task(text=text, name="chars")
    assert code == 0 and task_id

    captured: dict = {}

    class FakeTTSClient:

        def __init__(self, on_msg=None, on_err=None, on_progress=None):
            self.on_msg = on_msg
            self.on_err = on_err
            self.on_progress = on_progress
            self.speed = 1.0
            self.vol = 50
            self.model = None
            self._total_chars = 0
            captured["client"] = self

        def stream_msg(self, text: str, role=None, id=None):
            if self.on_msg:
                self.on_msg(b"audio", 0)

        def stream_complete(self):
            if self.on_msg:
                self.on_msg("done", 1)

    with patch("core.services.tools.tts_mgr.TTSClient", FakeTTSClient):
        code, msg = tts_mgr.start_task(task_id)
        assert code == 0, msg

        deadline = time.time() + 5
        while time.time() < deadline:
            task = tts_mgr.get_task(task_id)
            if task and task["status"] in ("success", "failed"):
                break
            time.sleep(0.05)

    assert captured["client"]._total_chars == expected


def test_tts_mgr_data_idle_timeout_uses_configured_threshold(tts_mgr: TTSMgr):
    code, _, task_id = tts_mgr.create_task(text="一行测试", name="idle-timeout")
    assert code == 0 and task_id

    class HangingTTSClient:

        def __init__(self, on_msg=None, on_err=None, on_progress=None):
            self._total_chars = 0
            self.speed = 1.0
            self.vol = 50
            self.model = None

        def stream_msg(self, text: str, role=None, id=None):
            return

        def stream_complete(self):
            return

    with patch("core.services.tools.tts_mgr.TTSClient", HangingTTSClient), patch(
        "core.services.tools.tts_mgr.TTS_DATA_IDLE_TIMEOUT", 0.15
    ):
        tts_mgr.start_task(task_id)
        deadline = time.time() + 5
        task = None
        while time.time() < deadline:
            task = tts_mgr.get_task(task_id)
            if task and task["status"] == "failed":
                break
            time.sleep(0.05)

    assert task is not None
    assert task["status"] == "failed"
    assert str(TTS_DATA_IDLE_TIMEOUT) in str(task.get("error_message", "")) or "0.15" in str(
        task.get("error_message", "")
    )


def test_tts_mgr_task_completion_timeout_cap(tts_mgr: TTSMgr):
    code, _, task_id = tts_mgr.create_task(text="总超时", name="total-timeout")
    assert code == 0 and task_id

    class HangingTTSClient:

        def __init__(self, on_msg=None, on_err=None, on_progress=None):
            self._total_chars = 0
            self.speed = 1.0
            self.vol = 50
            self.model = None

        def stream_msg(self, text: str, role=None, id=None):
            return

        def stream_complete(self):
            return

    with patch("core.services.tools.tts_mgr.TTSClient", HangingTTSClient), patch(
        "core.services.tools.tts_mgr.TTS_DATA_IDLE_TIMEOUT", 9999.0
    ), patch("core.services.tools.tts_mgr.TASK_COMPLETION_TIMEOUT", 0.2):
        tts_mgr.start_task(task_id)
        deadline = time.time() + 5
        task = None
        while time.time() < deadline:
            task = tts_mgr.get_task(task_id)
            if task and task["status"] == "failed":
                break
            time.sleep(0.05)

    assert task is not None
    assert task["status"] == "failed"
    assert "600" not in str(task.get("error_message", ""))  # patched to 0.2
    assert "0.2" in str(task.get("error_message", "")) or str(
        TASK_COMPLETION_TIMEOUT
    ) in str(task.get("error_message", ""))


def test_chat_tts_cache_replay_uses_streaming_protocol():
    socketio = MagicMock()
    ctx = ClientContext("sid-1", socketio)
    cached = b"\xff\xfb" + (b"a" * 7000)

    chunk_size = 3000
    for i in range(0, len(cached), chunk_size):
        ctx.on_tts_msg(cached[i : i + chunk_size], 0)
    ctx.on_tts_msg(">>[TTS] Completed", 1)

    audio_emits = [c for c in socketio.emit.call_args_list if c[0][0] == "dataAudio"]
    end_emit = [c for c in socketio.emit.call_args_list if c[0][0] == "endAudio"][-1]

    assert len(audio_emits) == 3
    assert end_emit[0][1]["content"] == ">>[TTS] Completed"
    assert end_emit[0][1]["content"] != cached


def test_chat_mgr_handle_tts_redis_cache_hit():
    handlers: dict = {}

    def register(event):
        def decorator(fn):
            handlers[event] = fn
            return fn

        return decorator

    socketio = MagicMock()
    socketio.on = register

    mgr = ChatMgr()
    mgr.init(socketio)
    handle_tts = handlers["tts"]

    sid = "sid-cache"
    mgr.clients[sid] = ClientContext(sid, socketio)

    payload = json.dumps(
        {"content": "朗读这段", "role": "longwan_v2", "id": "cache-id-1"},
        ensure_ascii=False,
    )

    socketio.reset_mock()
    ctx = ClientContext(sid, socketio)
    ctx.tts.process_msg = MagicMock()
    mgr.clients[sid] = ctx

    with patch("core.chat.chat_mgr.request", new=MagicMock(sid=sid)), patch(
        "core.chat.chat_mgr.tts_cache.get_complete_audio", return_value=b"abc"
    ):
        handle_tts(payload)

        ctx.tts.process_msg.assert_not_called()

    end_emit = [c for c in socketio.emit.call_args_list if c[0][0] == "endAudio"][-1]
    assert end_emit[0][1]["content"] == ">>[TTS] Completed"


@pytest.fixture
def tts_mgr(tmp_path, monkeypatch):
    monkeypatch.setattr("core.services.tools.tts_mgr.TTS_BASE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "core.services.tools.tts_mgr.get_media_duration", lambda _: 1.0
    )
    mgr = TTSMgr()
    mgr._tasks = {}
    return mgr
