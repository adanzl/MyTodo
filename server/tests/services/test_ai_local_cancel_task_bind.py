from unittest.mock import MagicMock

from core.ai.ai_local import AILocal


def test_streaming_cancel_uses_task_bound_to_request_id(monkeypatch):
    posted: list[str] = []

    def fake_post(url, **kwargs):
        posted.append(url)
        r = MagicMock()
        r.__enter__ = lambda s: s
        r.__exit__ = lambda *a: False
        r.raise_for_status = lambda: None
        return r

    monkeypatch.setattr("core.ai.ai_local.requests.post", fake_post)

    ai = AILocal(lambda *a: None, lambda *a: None)
    ai._active_stream_request_id = "req-b"
    ai.last_task_id = 999
    ai._task_id_by_request["req-a"] = 42

    ai.streaming_cancel(client_request_id="req-a")

    assert len(posted) == 1
    assert "42" in posted[0]
    assert "999" not in posted[0]


def test_streaming_cancel_skips_when_request_has_no_task(monkeypatch):
    posted: list[str] = []

    def fake_post(url, **kwargs):
        posted.append(url)
        return MagicMock()

    monkeypatch.setattr("core.ai.ai_local.requests.post", fake_post)

    ai = AILocal(lambda *a: None, lambda *a: None)
    ai._active_stream_request_id = "req-b"
    ai.last_task_id = 999

    ai.streaming_cancel(client_request_id="req-a")

    assert posted == []
    assert "req-a" in ai._pending_cancel
