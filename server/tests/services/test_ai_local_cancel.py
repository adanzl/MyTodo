from unittest.mock import MagicMock

from core.ai.ai_local import AILocal


def test_streaming_cancel_error_uses_captured_request_id(monkeypatch):
    seen: list[str] = []

    def on_err(_err, rid=""):
        seen.append(rid)

    ai = AILocal(lambda *a: None, on_err)
    ai._active_stream_request_id = "req-b"
    ai.last_task_id = 99

    def boom(*args, **kwargs):
        raise RuntimeError("cancel failed")

    monkeypatch.setattr("core.ai.ai_local.requests.post", boom)

    ai.streaming_cancel(client_request_id="req-a")

    assert seen == ["req-a"]
