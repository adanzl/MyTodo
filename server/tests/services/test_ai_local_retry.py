from unittest.mock import MagicMock, patch

import requests

from core.ai.ai_local import AILocal


def test_network_retry_without_output_keeps_conversation_id():
    ai = AILocal(on_msg=MagicMock(), on_err=MagicMock())
    ai.aiConversationId = "conv-keep"
    calls = {"n": 0}

    class EmptyStream:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def raise_for_status(self):
            return None

        def iter_lines(self):
            return iter([])

    def fake_post(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise requests.exceptions.ConnectionError("down")
        return EmptyStream()

    with patch("core.ai.ai_local.requests.post", side_effect=fake_post):
        ai.stream_msg("hi", client_request_id="rid-1")

    assert ai.aiConversationId == "conv-keep"
    ai.on_err.assert_not_called()
    assert calls["n"] == 2


def test_network_error_after_output_does_not_retry():
    ai = AILocal(on_msg=MagicMock(), on_err=MagicMock())

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def raise_for_status(self):
            return None

        def iter_lines(self):
            payload = (
                b'data: {"conversation_id":"c1","event":"message",'
                b'"answer":"hi","message_id":"m1"}'
            )
            yield payload
            raise requests.exceptions.ConnectionError("broken")

    with patch("core.ai.ai_local.requests.post", return_value=FakeResp()):
        ai.stream_msg("hello", client_request_id="rid-2")

    ai.on_err.assert_called_once()
