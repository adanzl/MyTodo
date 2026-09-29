"""Aliyun streaming ASR provider behavior."""

import json
from unittest.mock import MagicMock

from core.chat.aliyun_asr_client import AliyunAsrClient
from core.chat.asr_client import AsrClient, _AsrSession
from core.chat.asr_factory import create_asr_client
from core.config import config


def _cloud_client():
    results: list[tuple[str, str]] = []
    errors: list[Exception] = []
    asr = AliyunAsrClient(
        lambda text, rid="": results.append((text, rid)),
        lambda err: errors.append(err),
    )
    asr.sid = "sid-1"
    asr.sample_rate = 16000
    asr._ws_generation = 1
    session = _AsrSession("req-1", 1)
    asr._session = session
    asr._sessions_by_generation[1] = session
    asr._task_id = "11111111-1111-4111-8111-111111111111"
    asr.ws = MagicMock()
    return asr, results, errors


def _event(event: str, payload=None):
    return json.dumps(
        {
            "header": {
                "event": event,
                "task_id": "11111111-1111-4111-8111-111111111111",
            },
            "payload": payload or {},
        }
    )


def test_run_task_contains_qwen_streaming_parameters(monkeypatch):
    asr, _results, _errors = _cloud_client()
    monkeypatch.setattr(config, "ASR_ALIYUN_MODEL", "qwen-audio-3.1-asr-flash-streaming")
    monkeypatch.setattr(config, "ASR_ALIYUN_VAD_MODEL", "near_meeting_16k")
    monkeypatch.setattr(config, "ASR_ALIYUN_LANGUAGE_HINTS", "zh,en")
    monkeypatch.setattr(config, "ASR_ALIYUN_CONTEXT", "儿童科普问答，可能出现恐龙和英文科学名词")
    monkeypatch.setattr(config, "ASR_ALIYUN_VOCABULARY", '{"霸王龙":5,"Tyrannosaurus rex":5}')

    msg = json.loads(asr._run_task_message())

    assert msg["header"]["action"] == "run-task"
    assert msg["payload"]["model"] == "qwen-audio-3.1-asr-flash-streaming"
    params = msg["payload"]["parameters"]
    assert params["format"] == "pcm"
    assert params["sample_rate"] == 16000
    assert params["vad_model"] == "near_meeting_16k"
    assert params["language_hints"] == ["zh", "en"]
    assert params["vocabulary"] == {"霸王龙": 5, "Tyrannosaurus rex": 5}
    assert msg["payload"]["input"]["context"][0]["role"] == "user"


def test_partial_results_do_not_trigger_ai_until_task_finished():
    asr, results, errors = _cloud_client()
    handler = asr._make_on_message(1)

    handler(
        asr.ws,
        _event(
            "result-generated",
            {"output": {"sentence": {"sentence_id": 1, "sentence_end": False, "text": "霸王"}}},
        ),
    )
    assert results == []

    handler(
        asr.ws,
        _event(
            "result-generated",
            {"output": {"sentence": {"sentence_id": 1, "sentence_end": True, "text": "霸王龙为什么手很短？"}}},
        ),
    )
    assert results == []

    handler(asr.ws, _event("task-finished"))

    assert results == [("霸王龙为什么手很短？", "req-1")]
    assert errors == []
    asr.ws.close.assert_called_once()


def test_multiple_final_sentences_are_emitted_once_in_order():
    asr, results, _errors = _cloud_client()
    handler = asr._make_on_message(1)

    for sentence_id, text in ((2, "第二句。"), (1, "第一句。")):
        handler(
            asr.ws,
            _event(
                "result-generated",
                {"output": {"sentence": {"sentence_id": sentence_id, "sentence_end": True, "text": text}}},
            ),
        )

    handler(asr.ws, _event("task-finished"))
    assert results == [("第一句。第二句。", "req-1")]


def test_finish_before_task_started_flushes_audio_then_finishes():
    asr, results, errors = _cloud_client()
    asr.is_running = False
    asr.buffer.extend(b"\x01\x02\x03\x04")

    asr.end_asr()
    assert asr.ws.send_bytes.call_count == 0
    assert asr.ws.send.call_count == 0

    asr._make_on_message(1)(asr.ws, _event("task-started"))

    asr.ws.send_bytes.assert_called_once_with(b"\x01\x02\x03\x04")
    assert asr.ws.send.call_count == 1
    finish = json.loads(asr.ws.send.call_args.args[0])
    assert finish["header"]["action"] == "finish-task"
    assert results == []
    assert errors == []


def test_factory_keeps_local_funasr_available(monkeypatch):
    monkeypatch.setattr(config, "ASR_PROVIDER", "funasr")
    local = create_asr_client()
    assert type(local) is AsrClient

    monkeypatch.setattr(config, "ASR_PROVIDER", "aliyun")
    cloud = create_asr_client()
    assert isinstance(cloud, AliyunAsrClient)
