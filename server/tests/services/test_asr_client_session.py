"""ASR 会话：取消不应影响下一次录音；迟到结果不应串到新会话。"""

from unittest.mock import MagicMock

from core.chat.asr_client import AsrClient, _AsrSession


def test_cancel_session_does_not_block_next_result():
    results: list[tuple[str, str]] = []

    def on_result(text, rid=""):
        results.append((text, rid))

    asr = AsrClient(on_result, lambda _e: None)
    asr.sid = "test"
    asr.begin_session("req-a")
    asr.cancel_session("req-a")

    asr.begin_session("req-b")
    asr._ws_generation = 1
    asr._ws_generation += 1
    ws_gen = asr._ws_generation
    session = _AsrSession("req-b", ws_gen)
    asr._session = session
    asr._sessions_by_generation[ws_gen] = session

    handler = asr._make_on_message(ws_gen)
    handler(MagicMock(), '{"mode":"offline","text":"你好"}')

    assert results == [("你好", "req-b")]


def test_stale_ws_generation_is_ignored():
    results: list[tuple[str, str]] = []
    asr = AsrClient(lambda t, r="": results.append((t, r)), lambda _e: None)
    asr.sid = "test"
    asr._ws_generation = 2
    asr._sessions_by_generation[2] = _AsrSession("req-a", 2)
    asr._session = asr._sessions_by_generation[2]

    stale = asr._make_on_message(1)
    stale(MagicMock(), '{"mode":"offline","text":"迟到"}')
    assert results == []

    current = asr._make_on_message(2)
    current(MagicMock(), '{"mode":"offline","text":"当前"}')
    assert results == [("当前", "req-a")]


def test_cancelled_session_drops_late_result():
    results: list[tuple[str, str]] = []
    asr = AsrClient(lambda t, r="": results.append((t, r)), lambda _e: None)
    asr.sid = "test"
    asr._sessions_by_generation[1] = _AsrSession("req-a", 1, cancelled=True)
    asr._session = asr._sessions_by_generation[1]

    handler = asr._make_on_message(1)
    handler(MagicMock(), '{"mode":"offline","text":"不应出现"}')
    assert results == []


def test_same_connection_late_a_after_begin_b_without_new_generation():
    """复用连接时 begin B 必须作废 A；迟到 A 不能归到 B。"""
    results: list[tuple[str, str]] = []
    asr = AsrClient(lambda t, r="": results.append((t, r)), lambda _e: None)
    asr.sid = "test"
    asr._ws_generation = 1
    asr._sessions_by_generation[1] = _AsrSession("req-a", 1)
    asr._session = asr._sessions_by_generation[1]
    asr.is_running = True
    asr.ws = MagicMock()

    asr.begin_session("req-b")
    assert asr._sessions_by_generation[1].cancelled is True
    assert asr.ws is None

    handler_a = asr._make_on_message(1)
    handler_a(MagicMock(), '{"mode":"offline","text":"late result from A"}')
    assert results == []

    asr._ws_generation += 1
    gen_b = asr._ws_generation
    asr._sessions_by_generation[gen_b] = _AsrSession("req-b", gen_b)
    asr._session = asr._sessions_by_generation[gen_b]
    handler_b = asr._make_on_message(gen_b)
    handler_b(MagicMock(), '{"mode":"offline","text":"B ok"}')
    assert results == [("B ok", "req-b")]


def test_stale_on_close_does_not_clear_active_connection():
    """A 关闭后 B 已连接并缓冲音频，A 迟到的 on_close 不能清空 B 的状态。"""
    asr = AsrClient(lambda *_a: None, lambda _e: None)
    asr.sid = "test"
    asr._ws_generation = 2
    asr.ws = MagicMock()
    asr.is_running = True
    asr.buffer.extend(b"\x00\x01")

    stale_close = asr._make_on_close(1)
    stale_close(MagicMock(), 1000, "old gone")

    assert asr.ws is not None
    assert asr.is_running is True
    assert len(asr.buffer) == 2

    current_close = asr._make_on_close(2)
    current_close(MagicMock(), 1000, "current gone")
    assert asr.ws is None
    assert asr.is_running is False
    assert len(asr.buffer) == 0


def test_stale_on_open_does_not_mark_running():
    asr = AsrClient(lambda *_a: None, lambda _e: None)
    asr.sid = "test"
    asr._ws_generation = 2
    asr.is_running = False

    stale_open = asr._make_on_open(1)
    stale_open(MagicMock())

    assert asr.is_running is False


def test_cancel_session_a_does_not_teardown_active_b():
    asr = AsrClient(lambda *_a: None, lambda _e: None)
    asr.sid = "test"
    asr._ws_generation = 2
    sess_a = _AsrSession("req-a", 1)
    sess_b = _AsrSession("req-b", 2)
    asr._sessions_by_generation[1] = sess_a
    asr._sessions_by_generation[2] = sess_b
    asr._session = sess_b
    asr.ws = MagicMock()
    asr.is_running = True

    asr.cancel_session("req-a")

    assert sess_a.cancelled is True
    assert sess_b.cancelled is False
    assert asr.ws is not None
