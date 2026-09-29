from core.chat.tts_phrase_buffer import TtsPhraseBuffer


def test_phrase_breaks_on_punctuation():
    buf = TtsPhraseBuffer(first_soft_limit=30)
    out = buf.feed("你好，这是第一句。")
    assert out == ["你好，这是第一句。"]
    out2 = buf.feed("继续第二句！还有第三段。")
    assert any("继续第二句！" in piece for piece in out2)


def test_hard_limit_splits_long_segment():
    buf = TtsPhraseBuffer(first_soft_limit=10, phrase_soft_limit=20, hard_limit=25)
    chunk = "a" * 30
    out = buf.feed(chunk)
    assert out
    assert sum(len(x) for x in out) <= 30


def test_flush_rest_returns_tail():
    buf = TtsPhraseBuffer()
    buf.feed("尾巴文本")
    tail = buf.flush_rest()
    assert tail == "尾巴文本"
