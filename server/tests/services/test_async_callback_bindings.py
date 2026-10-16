"""回调「绑定时刻」与线程归属的并发回归。

这类缺陷的共同点：回调来自 SDK / ASR 的**真实线程**，交回 hub 后是在稍后的时刻
执行的；如果那时才去读「当前」状态，而期间会话已经切换，就会张冠李戴。

- SDK 异常分支曾在 SDK 工作线程直接调用 `on_err`（最终 `socketio.emit`）→
  跨线程使用 hub 的 gevent socket。
- ASR 错误回调曾在执行时才读 `self.asr._session` → 期间切换会话后，
  旧连接的错误会把**新**请求标记为失败。
- TTS 完成事件曾在执行时才读 `self._cache_session` / 延迟缓存 → 期间开始的新
  会话会被误判为「已完成」并解绑（实测可复现）。

修复方式是「就地绑定」：投递的闭包捕获它当时的会话/快照，而不是执行时再读。
"""

import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.chat.chat_mgr import ClientContext
from core.tools.hub_dispatch import run_pending_hub_tasks


# ---------------- SDK 异常分支必须交回 hub ----------------


def test_sdk_error_callback_runs_on_hub_thread():
    """SDK 操作抛出的异常，其 `on_err` 必须在 hub 线程执行。

    原先在 SDK 工作线程直接调用 —— 而 `on_err` 最终会 `socketio.emit`，
    那是在用归属 hub 的 gevent socket。
    """
    from core.tts.tts_client import TTSClient

    tts = TTSClient()
    seen = {}

    def record(err):
        seen['tid'] = threading.get_ident()
        seen['err'] = err

    tts.on_err = record

    def boom():
        raise RuntimeError('sdk boom')

    tts._sdk.submit(lambda: tts._submit_sdk(boom, label='test'), wait=True)
    tts._sdk.wait_pending()

    assert 'err' not in seen, '错误回调不应在 SDK 工作线程上直接执行'

    run_pending_hub_tasks()

    assert seen.get('tid') == threading.get_ident(), '错误回调没有回到 hub 线程'
    assert 'sdk boom' in str(seen.get('err'))


# ---------------- ASR 错误必须绑定回调时的会话 ----------------


def test_asr_error_uses_session_at_callback_time():
    """ASR 错误要归属**回调发生时**的会话，而不是执行时的当前会话。

    否则：旧连接的报错会把期间新发起的请求标成失败。
    """
    socketio = MagicMock()
    ctx = ClientContext('sid-asr-bind', socketio)
    ctx.asr = MagicMock()
    ctx.asr._session = SimpleNamespace(request_id='rid-OLD', attempt=1)
    ctx.ai = MagicMock()
    ctx.ai.user = 'user-1'

    captured = []
    ctx.on_err = lambda err, rid='', **kw: captured.append((rid, kw))

    ctx.on_asr_err(RuntimeError('asr down'))   # 投递（绑定 OLD）
    ctx.asr._session = SimpleNamespace(request_id='rid-NEW', attempt=2)   # 期间切换会话

    run_pending_hub_tasks()

    assert captured, '错误未上报'
    assert captured[0][0] == 'rid-OLD', (
        f'错误被归属到了错误的会话: {captured[0][0]!r}（应为 rid-OLD）'
    )


def test_asr_error_carries_the_bound_attempt():
    """错误必须带上**回调时绑定**的代次，而不是执行时读到的最新代次。

    用户重试会让 attempt +1；若用最新值，旧连接的错误会被算到新一轮请求头上，
    把新尝试直接标成失败（`on_err` 内部会用 matches_attempt 校验，传对了才会忽略）。
    """
    socketio = MagicMock()
    ctx = ClientContext('sid-asr-attempt', socketio)
    ctx.asr = MagicMock()
    ctx.asr._session = SimpleNamespace(request_id='rid-1', attempt=1)
    ctx.ai = MagicMock()
    ctx.ai.user = 'user-1'

    captured = []
    ctx.on_err = lambda err, rid='', **kw: captured.append(kw.get('attempt'))

    ctx.on_asr_err(RuntimeError('stale asr error'))
    # 期间用户重试：新一轮请求的代次变成 2
    ctx.asr._session = SimpleNamespace(request_id='rid-1', attempt=2)

    run_pending_hub_tasks()

    assert captured == [1], (
        f'错误带上了错误的代次 {captured}（应为 [1]）—— '
        '用最新代次会把旧错误算到新一轮头上'
    )


def test_stale_asr_error_is_ignored_by_on_err():
    """端到端：旧连接的错误在新一轮请求下必须被忽略，不能把新尝试标成失败。"""
    from core.tools import hub_dispatch

    socketio = MagicMock()
    ctx = ClientContext('sid-asr-stale', socketio)
    ctx.asr = MagicMock()
    ctx.asr._session = SimpleNamespace(request_id='rid-9', attempt=1)
    ctx.ai = MagicMock()
    ctx.ai.user = 'user-1'

    # 让 matches_attempt 认为「数据库里已是 attempt=2」，即用户已重试
    with patch('core.chat.chat_mgr.chat_request_store') as store:
        store.get_attempt.return_value = 2
        store.matches_attempt.return_value = False
        store.mark_failed.return_value = True

        ctx.on_asr_err(RuntimeError('old connection died'))
        hub_dispatch.run_pending_hub_tasks()

    assert not store.mark_failed.called, (
        '旧连接的错误把新一轮请求标记为失败了（应被 matches_attempt 拦下）'
    )
    assert socketio.emit.call_count == 0, '过期错误不应上报给前端'


# ---------------- TTS 完成事件必须绑定自己那份缓存 ----------------


def test_tts_completion_binds_its_own_deferred_cache():
    """完成事件提交的是它自己那份内容，且不得清掉新会话的状态。"""
    from core.tts.tts_client import TTSClient

    tts = TTSClient()
    tts.start_deferred_cache('msg-old')
    tts.on_data(b'audio-old')
    tts.prepare_deferred_cache('old text')

    tts.on_complete()          # 绑定旧会话，投递到 hub（此刻尚未执行）

    # 期间开始新会话
    tts.start_deferred_cache('msg-new')
    tts.on_data(b'audio-new')
    tts.prepare_deferred_cache('new text')

    with patch('core.chat.tts_cache.begin_session') as begin, \
         patch('core.chat.tts_cache.finalize_session') as finalize, \
         patch('core.tts.tts_client.rds_mgr.append_value') as append:
        begin.return_value = {'audio_key': 'k', 'meta_key': 'm', 'text_hash': 'h'}
        run_pending_hub_tasks()

    assert begin.called, '完成事件没有提交缓存'
    called_msg_id = begin.call_args[0][0]
    assert called_msg_id == 'msg-old', (
        f'完成事件提交了错误的会话: {called_msg_id!r}（应为 msg-old）'
    )
    assert append.called
    assert append.call_args[0][1] == b'audio-old', (
        f'提交了错误的内容: {append.call_args[0][1]!r}（应为旧会话的音频）'
    )
    assert finalize.called

    # 新会话的状态必须完好 —— 不能被旧完成事件清掉
    assert tts._deferred_cache_msg_id == 'msg-new', (
        f'新会话的绑定被旧完成事件清掉了: {tts._deferred_cache_msg_id!r}'
    )
    assert bytes(tts._deferred_cache_audio) == b'audio-new', '新会话的音频被清掉了'


def test_tts_completion_does_not_finalize_the_new_session():
    """旧完成事件不得把**新**会话标记为完成（否则新音频会丢失绑定）。"""
    from core.tts.tts_client import TTSClient

    tts = TTSClient()
    # 注意顺序：start_deferred_cache 会把 _cache_session 置为 None，
    # 所以旧会话必须在它**之后**设置，否则 on_complete 绑定到的是 None。
    tts.start_deferred_cache('msg-old')
    tts.prepare_deferred_cache('old')
    old_session = {'audio_key': 'old', 'meta_key': 'm', 'text_hash': 'h'}
    tts._cache_session = old_session

    tts.on_complete()          # 绑定 old_session

    new_session = {'audio_key': 'new', 'meta_key': 'm2', 'text_hash': 'h2'}
    tts.start_immediate_cache('msg-new', 'new text', 'longwan_v3', 1.0)

    with patch('core.chat.tts_cache.finalize_session') as finalize:
        run_pending_hub_tasks()

    finalized = [c.args[0] for c in finalize.call_args_list]
    assert old_session in finalized, '旧会话未被结束'
    assert tts._cache_session is not None, '新会话的绑定被旧完成事件清掉了'


def test_finalize_cache_with_explicit_none_does_nothing():
    """`finalize_cache(None)` 表示「我那个旧会话不存在」，不得碰当前会话。

    这是 `_UNSET` 哨兵要解决的边界：若把显式传入的 None 当成「结束当前缓存」，
    那么旧的延迟缓存完成事件（捕获到的 session 恰为 None）在 hub 上延时执行时，
    只要新的即时缓存已经开始，就会把**新缓存**标记为完成并解绑 ——
    新合成的音频随之丢失。
    """
    from unittest.mock import patch

    from core.tts.tts_client import TTSClient

    tts = TTSClient()
    tts.start_immediate_cache('msg-new', 'new text', 'longwan_v3', 1.0)
    new_session = tts._cache_session
    assert new_session is not None

    with patch('core.chat.tts_cache.finalize_session') as finalize, \
         patch('core.chat.tts_cache.abort_session') as abort:
        tts.finalize_cache(None)          # 明确表示「旧缓存不存在」

    assert not finalize.called, '显式传 None 时不应结束任何会话'
    assert not abort.called
    assert tts._cache_session is new_session, (
        '新缓存的绑定被「旧缓存不存在」的完成事件清掉了'
    )


def test_finalize_cache_without_argument_still_ends_current():
    """不传参数仍是「结束当前会话」——哨兵不能把默认行为也改掉。"""
    from unittest.mock import patch

    from core.tts.tts_client import TTSClient

    tts = TTSClient()
    tts.start_immediate_cache('msg-cur', 'text', 'longwan_v3', 1.0)
    current = tts._cache_session

    with patch('core.chat.tts_cache.finalize_session') as finalize:
        tts.finalize_cache()

    assert finalize.call_args_list == [((current,),)] or (
        finalize.called and finalize.call_args[0][0] is current
    ), '不传参数时应结束当前会话'
    assert tts._cache_session is None, '当前会话结束后应解绑'


def test_finalize_cache_with_specific_session_keeps_newer_binding():
    """传入具体会话时，只能解绑它自己 —— 不能把后来者的绑定清掉。"""
    from unittest.mock import patch

    from core.tts.tts_client import TTSClient

    tts = TTSClient()
    old = object()
    tts.start_immediate_cache('msg-new', 'text', 'longwan_v3', 1.0)
    newer = tts._cache_session

    with patch('core.chat.tts_cache.finalize_session') as finalize:
        tts.finalize_cache(old)

    assert finalize.called and finalize.call_args[0][0] is old
    assert tts._cache_session is newer, '后来者的绑定被清掉了'
