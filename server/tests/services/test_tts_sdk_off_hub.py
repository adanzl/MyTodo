"""TTS SDK 操作的线程归属与 hub 不阻塞（P1 回归）。

故障背景（2026-10-16 全面扫描）：

- DashScope `SpeechSynthesizer.streaming_complete()` 内部用原生
  `threading.Event.wait(timeout=600000ms)`，`call()` 更是等到整段合成结束；
  `monkey.patch_all(thread=False)` 使这些等待占住整个 OS 线程（hub）。
- SDK 的 WebSocket 与创建它的线程绑定，跨线程使用会抛
  "Cannot switch to a different thread"。

修复方式：所有 SDK 操作投递到同一个专用 OS 线程，hub 只投递不等待。
"""

import threading

from gevent import sleep, spawn

from core.tts.tts_worker import SdkWorker


def test_submit_runs_action_on_the_worker_thread():
    """动作必须在专用线程执行，而不是调用方线程。"""
    worker = SdkWorker('test-1')
    caller_tid = threading.get_ident()
    seen = {}

    worker.submit(lambda: seen.update(tid=threading.get_ident()), wait=True)

    assert seen['tid'] != caller_tid, 'SDK 操作不得在调用方（hub）线程上执行'
    assert seen['tid'] == worker._thread.ident


def test_submit_is_non_blocking_by_default():
    """默认「点火即走」：hub 投递后立刻返回，不等待 SDK 完成。

    这正是修复 hub 阻塞的关键——`streaming_complete()` 最长可等 10 分钟。
    """
    worker = SdkWorker('test-2')
    release = threading.Event()
    started = threading.Event()

    def slow_action():
        started.set()
        release.wait(5)

    worker.submit(slow_action)

    # 未指定 wait 时必须立即返回（动作还在跑）
    assert started.wait(2), '动作没有开始执行'
    assert not release.is_set()
    release.set()


def test_submit_wait_returns_value_and_propagates_error():
    worker = SdkWorker('test-3')

    assert worker.submit(lambda: 42, wait=True) == 42

    def boom():
        raise ValueError('sdk failed')

    try:
        worker.submit(boom, wait=True)
    except ValueError as e:
        assert 'sdk failed' in str(e)
    else:
        raise AssertionError('异常应传播给等待方')


def test_submit_wait_times_out_without_hanging():
    """等待超时必须抛 TimeoutError，不能无限阻塞。"""
    worker = SdkWorker('test-4')
    release = threading.Event()

    worker.submit(lambda: release.wait(10))

    try:
        worker.submit(lambda: None, wait=True, timeout=0.3)
    except TimeoutError:
        pass
    else:
        raise AssertionError('超时应抛 TimeoutError')
    finally:
        release.set()


def test_actions_run_in_submission_order():
    """动作必须按投递顺序串行执行 —— 文本片段的先后有意义。"""
    worker = SdkWorker('test-5')
    order = []

    for i in range(20):
        worker.submit(lambda i=i: order.append(i), wait=True)

    assert order == list(range(20))


def test_tts_client_does_not_block_hub(tmp_path):
    """端到端：TTSClient 的 SDK 调用不得占住 hub。

    用一个假的 synthesizer 模拟「SDK 调用耗时 2 秒」，观察 hub 在调用窗口内
    是否还能被调度。修复前这些调用直接跑在 hub 上，窗口内几乎没有心跳。
    """
    import os
    import subprocess
    import sys
    import textwrap

    server_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = os.path.join(str(tmp_path), '_probe_tts.py')
    with open(script, 'w', encoding='utf-8') as f:
        f.write(textwrap.dedent("""
            from gevent import monkey
            monkey.patch_all(subprocess=True, thread=False, queue=False)

            import time
            from gevent import sleep, spawn

            witness = []
            def witness_loop():
                while True:
                    witness.append(time.monotonic())
                    sleep(0.01)
            spawn(witness_loop)
            sleep(0.3)

            import core.tts.tts_client as tts_client

            # 用假的 synthesizer 模拟「SDK 调用同步等待 2 秒」
            class FakeSynth:
                def streaming_call(self, text):
                    time.sleep(2.0)
                def streaming_complete(self):
                    time.sleep(2.0)
                def call(self, text):
                    time.sleep(2.0)
                def streaming_cancel(self):
                    time.sleep(2.0)

            class FakeClient(tts_client.TTSClient):
                def __init__(self):
                    # 不调 super().__init__（会绑定真实 SDK），补齐本用例需要的字段
                    from core.tts.tts_worker import SdkWorker
                    self._sdk = SdkWorker('fake-tts')
                    self.role = 'longwan_v2'
                    self.vol = 50
                    self.speed = 1.0
                    self.id = ''
                    self.synthesizer = FakeSynth()
                    self._errored = False
                def on_err(self, e):
                    pass

            def max_gap(t0, t1):
                ticks = [t for t in witness if t0 <= t <= t1]
                if len(ticks) < 2:
                    return t1 - t0
                return max(b - a for a, b in zip(ticks, ticks[1:]))

            now = time.monotonic()
            base = max_gap(now - 1.0, now)
            print('BASE_GAP=%.4f' % base)

            c = FakeClient()
            t0 = time.monotonic()
            c.stream_msg('你好', 'longwan_v2', 'm1')   # 修复前：此处阻塞 hub 2 秒
            c.process_msg('你好', 'longwan_v2', 'm2')
            t1 = time.monotonic()

            print('ELAPSED=%.3f' % (t1 - t0))
            print('MAX_GAP=%.4f' % max_gap(t0, t1))
            print('DONE')
        """))

    env = dict(os.environ)
    env.setdefault('PYTHONIOENCODING', 'utf-8')
    env['PYTHONPATH'] = os.pathsep.join([server_root, env.get('PYTHONPATH', '')]).rstrip(os.pathsep)
    env['RDS_LOCAL_FILE'] = str(tmp_path / 'rds_probe.json')

    try:
        proc = subprocess.run(
            [sys.executable, script],
            cwd=server_root, env=env, capture_output=True, text=True,
            errors='replace', timeout=90,
        )
    except subprocess.TimeoutExpired:
        raise AssertionError('TTS 探针挂死（hub 被阻塞）')

    assert proc.returncode == 0, f'探针失败:\n{proc.stdout}\n{proc.stderr}'

    def value(key):
        line = [l for l in proc.stdout.splitlines() if l.startswith(key + '=')]
        assert line, f'未产出 {key}:\n{proc.stdout}\n{proc.stderr}'
        return float(line[0].split('=', 1)[1])

    # 投递必须立即返回（修复前这里会是 4 秒：两次各 2 秒）
    assert value('ELAPSED') < 1.0, (
        f"投递耗时 {value('ELAPSED'):.2f}s —— 应在投递后立即返回，不等待 SDK 完成"
    )
    gap = value('MAX_GAP')
    assert gap <= 0.25, (
        f'hub 被阻塞了约 {gap:.2f}s：SDK 调用仍在 hub 线程上同步执行'
    )


def test_each_client_gets_its_own_sdk_thread():
    """每个 TTSClient 必须有自己的 SDK 线程。

    若共用一条线程，A 的 `streaming_complete()`（最长等 10 分钟）会把 B 的合成
    全部堵住 —— 与 hub_dispatch 曾经踩过的串行化同类。
    """
    from core.tts.tts_client import TTSClient

    a, b = TTSClient(), TTSClient()
    try:
        assert a._sdk is not b._sdk, '不同客户端不应共用执行器'

        seen = {}
        a._sdk.submit(lambda: seen.update(a=threading.get_ident()), wait=True)
        b._sdk.submit(lambda: seen.update(b=threading.get_ident()), wait=True)

        assert seen['a'] != seen['b'], '不同客户端的 SDK 操作应落在不同线程'
    finally:
        a._sdk.wait_pending()
        b._sdk.wait_pending()


def test_one_client_reuses_a_single_thread():
    """同一个客户端内部必须固定用一条线程，否则连接会被跨线程使用。"""
    from core.tts.tts_client import TTSClient

    client = TTSClient()
    try:
        seen = []
        for _ in range(3):
            client._sdk.submit(lambda: seen.append(threading.get_ident()), wait=True)
        assert len(set(seen)) == 1, '同一客户端的 SDK 操作必须落在同一条线程上'
    finally:
        client._sdk.wait_pending()


def test_idle_worker_stops_and_restarts():
    """空闲超时后线程退出，再次投递要能自动拉起（且不丢任务）。"""
    worker = SdkWorker('test-idle', idle_timeout=0.2)

    worker.submit(lambda: None, wait=True)
    assert worker.is_running

    sleep(0.6)
    assert not worker.is_running, '空闲后线程应自行退出，避免线程累积'

    # 重新投递必须照常执行（防「退出与投递竞态」导致任务丢失）
    box = {}
    worker.submit(lambda: box.update(ok=True), wait=True)
    assert box.get('ok') is True, '线程重启后任务丢失'


def test_submit_after_idle_does_not_lose_tasks():
    """并发投递场景下也不能丢任务（退出与入队的竞态）。"""
    worker = SdkWorker('test-race', idle_timeout=0.2)
    worker.submit(lambda: None, wait=True)
    sleep(0.35)   # 让线程在空闲边缘退出

    results = []
    threads = [
        threading.Thread(target=lambda i=i: worker.submit(lambda: results.append(i), wait=True))
        for i in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    for t in threads:
        assert not t.is_alive()

    assert sorted(results) == [0, 1, 2, 3, 4], f'有任务丢失: {results}'


# ---------------- 结束/取消不得互相堵住 ----------------


class _SlowSyncSynth:
    """假 synthesizer：同步结束会长时间等待，异步结束立刻返回。"""

    _is_started = True

    def __init__(self):
        self.cancelled = False
        self.sync_complete_called = False

    def streaming_complete(self, *args, **kwargs):  # 同步版本：会一直等（SDK 最长 10 分钟）
        self.sync_complete_called = True
        time.sleep(30)

    def async_streaming_complete(self, *args, **kwargs):  # 异步版本：发指令即返回
        pass

    def streaming_cancel(self, *args, **kwargs):
        self.cancelled = True


def test_cancel_is_not_blocked_by_complete():
    """取消必须能在结束动作之后立刻执行。

    这是 TTS 换到专用线程后引入的回归：`streaming_complete()` 会等最长 10 分钟，
    而 SDK 调用走**同一条串行队列**，于是排在其后的 `streaming_cancel()` 一起被堵住
    ——取消恰恰是用来打断这等待的。

    用会长时间阻塞的假同步实现来验证：若代码走了同步版本，`wait_pending` 会超时。
    """
    from core.tts.tts_client import TTSClient

    tts = TTSClient()
    synth = _SlowSyncSynth()
    tts.synthesizer = synth
    try:
        tts.stream_complete()
        tts.streaming_cancel()

        # 队列若被结束动作占住，这里会超时失败
        tts._sdk.wait_pending(timeout=2.0)

        assert not synth.sync_complete_called, (
            '不应调用同步 streaming_complete()：它会占住队列、堵死取消'
        )
        assert synth.cancelled is True, '取消未被执行'
    finally:
        tts._sdk.discard_pending()


def test_complete_uses_async_variant():
    """结束动作应使用 SDK 的异步接口，由回调判断完成。"""
    from unittest.mock import MagicMock

    from core.tts.tts_client import TTSClient

    tts = TTSClient()
    synth = MagicMock()
    synth._is_started = True
    tts.synthesizer = synth

    tts.stream_complete()
    tts._sdk.wait_pending()

    assert synth.async_streaming_complete.called, '应使用 async_streaming_complete()'
    assert not synth.streaming_complete.called


# ---------------- 空流结束不得误报 ----------------


def test_stream_complete_without_any_text_does_not_error():
    """从未发送过文本时，结束动作不得创建实例、也不得报「尚未启动」。

    原实现在投递时就调 `_ensure_synthesizer()`，会先造出一个从未 started 的实例，
    再调结束方法 → SDK 抛 `speech synthesizer has not been started`。
    判断必须放在**动作内部**，那时才能确定队列里确实没有待发送的文本。

    断言「从未构造过 synthesizer」而不是「最终为 None」：后者会被动作内部的
    未启动清理分支抹平（实例先被创建、再被清成 None），测不出这个回归。
    """
    from unittest.mock import patch

    from core.tts.tts_client import TTSClient

    with patch('core.tts.tts_client.SpeechSynthesizer') as synth_cls:
        tts = TTSClient()
        errors = []
        tts.on_err = errors.append

        tts.stream_complete()          # 从未 stream_msg / process_msg
        tts._sdk.wait_pending()

        assert not synth_cls.called, '不应为空的流创建 synthesizer'
        assert errors == [], f'不应报错: {errors}'
        assert tts.synthesizer is None


def test_stream_complete_when_synth_not_started_is_silent():
    """会话存在但未真正启动（例如启动失败）时，结束动作要静默清理。"""
    from core.tts.tts_client import TTSClient

    class _NotStarted:
        _is_started = False

        def async_streaming_complete(self, *a, **k):
            raise AssertionError('未启动的会话不应收到结束指令')

    tts = TTSClient()
    errors = []
    tts.on_err = errors.append
    tts.synthesizer = _NotStarted()

    tts.stream_complete()
    tts._sdk.wait_pending()

    assert errors == []
    assert tts.synthesizer is None, '未启动的实例应被清理'


# ---------------- 取消要丢弃待发送片段 ----------------


def test_cancel_discards_queued_text_segments():
    """取消后，队列里尚未发送的文本片段不得再发出去。"""
    from core.tts.tts_client import TTSClient

    sent = []

    class _Synth:
        _is_started = True

        def streaming_call(self, text):
            sent.append(text)

        def streaming_cancel(self):
            pass

    tts = TTSClient()
    tts.synthesizer = _Synth()
    # 占住队列，让后续片段只能排队
    blocker = threading.Event()
    tts._sdk.submit(lambda: blocker.wait(10))
    sleep(0.05)

    tts.stream_msg('片段1')
    tts.stream_msg('片段2')
    tts.streaming_cancel()          # 丢弃上面两个未执行的片段
    blocker.set()
    tts._sdk.wait_pending(timeout=3)

    assert sent == [], f'被取消的片段仍然发了出去: {sent}'


def test_discard_pending_releases_waiters():
    """被丢弃的等待方要收到完成信号，而不是一直卡到超时。"""
    worker = SdkWorker('test-discard')
    blocker = threading.Event()
    worker.submit(lambda: blocker.wait(10))
    sleep(0.05)

    box = {}

    def waiter():
        # wait=True 的调用被丢弃时应立即返回，而不是等满 5 秒
        worker.submit(lambda: None, wait=True, timeout=5)
        box['returned'] = True

    t = threading.Thread(target=waiter, daemon=True)
    t.start()
    sleep(0.1)
    dropped = worker.discard_pending()
    blocker.set()

    t.join(2)
    assert dropped == 1, f'应丢弃 1 个动作，实际 {dropped}'
    assert box.get('returned') is True, '等待方被丢弃后没有及时返回'
