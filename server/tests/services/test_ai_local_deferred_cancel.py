from unittest.mock import MagicMock

from core.ai.ai_local import AILocal


def test_cancel_before_task_id_defers_and_does_not_use_last_task_id(monkeypatch):
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
    ai.last_task_id = 111

    ai.streaming_cancel(client_request_id="req-b")

    assert posted == []
    assert "req-b" in ai._pending_cancel


def test_deferred_cancel_fires_on_task_id_bound_to_same_request(monkeypatch):
    posted: list[str] = []
    chunks = [
        b'data: {"event":"message","answer":"x","message_id":"m1","conversation_id":"c1","task_id":222}',
        b'data: {"event":"message_end","metadata":{},"message_id":"m1","conversation_id":"c1","task_id":222}',
    ]

    def fake_post(url, **kwargs):
        posted.append(url)
        if "chat-messages" in url and url.endswith("/stop"):
            r = MagicMock()
            r.__enter__ = lambda s: s
            r.__exit__ = lambda *a: False
            r.raise_for_status = lambda: None
            return r
        r = MagicMock()
        r.__enter__ = lambda s: r
        r.__exit__ = lambda *a: False
        r.raise_for_status = lambda: None
        r.iter_lines = lambda: iter(chunks)
        return r

    monkeypatch.setattr("core.ai.ai_local.requests.post", fake_post)

    ai = AILocal(lambda *a: None, lambda *a: None)
    ai.last_task_id = 111
    ai.streaming_cancel(client_request_id="req-b")

    ai.stream_msg("hello", client_request_id="req-b")

    stop_urls = [u for u in posted if u.endswith("/stop")]
    assert len(stop_urls) == 1
    assert "222" in stop_urls[0]
    assert "111" not in stop_urls[0]
