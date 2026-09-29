from unittest.mock import MagicMock

from core.ai.ai_local import AILocal


def test_stream_msg_passes_client_request_id_to_callbacks(monkeypatch):
    seen_msg: list[str] = []
    seen_err: list[str] = []

    def on_msg(_text, _id, _type, client_request_id=""):
        seen_msg.append(client_request_id)

    def on_err(_err, client_request_id=""):
        seen_err.append(client_request_id)

    ai = AILocal(on_msg, on_err)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield b'data: {"event":"message","answer":"a","message_id":"m1","conversation_id":"c1","task_id":1}'
            yield b'data: {"event":"message_end","metadata":{},"message_id":"m1","conversation_id":"c1"}'

    monkeypatch.setattr(
        "core.ai.ai_local.requests.post",
        lambda *a, **k: FakeResponse(),
    )

    ai.stream_msg("hello", client_request_id="req-bind-1")

    assert seen_msg == ["req-bind-1", "req-bind-1"]
    assert seen_err == []
