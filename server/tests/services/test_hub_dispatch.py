"""`hub_dispatch` 的跨线程投递与并发测试。

真实故障（2026-10-16）：ASR 的 ws 回调运行在真实 OS 线程，却直接做 Redis 读写、
`socketio.emit`、发起 `requests` 流式请求——这些都是 hub 归属对象。要么抛
"Cannot switch to a different thread"，要么污染连接池。

这里锁住两条不变量：
1. 投递的函数最终在**启动消费循环的那个线程**上执行，而不是投递方线程
   （`gevent.spawn` 做不到这点，它只是新建 greenlet）；
2. 多个任务**并发**执行，不被消费循环串行化 —— `stream_msg` 会读到整段流结束，
   串行化会让一个用户的对话把其它用户全堵住。

每个用例都新建 `HubDispatcher` 实例：消费循环是整个进程的长驻 greenlet，
若共用模块级单例，前一个用例留下的循环会抢走队列里的任务，
使"是否串行"无法被确定地测出来。
"""

import queue
import threading

from gevent import sleep

from core.tools.hub_dispatch import HubDispatcher, run_pending_hub_tasks


def _drain(dispatcher, coop_drain=True):
    """启动实例的消费循环，并按需清空遗留任务。"""
    while True:
        try:
            dispatcher._queue.get_nowait()
        except queue.Empty:
            break
    dispatcher.start()
    if coop_drain:
        sleep(0.05)  # 让消费循环真正跑起来
    return dispatcher


def _wait_for(predicate, timeout=5.0):
    deadline = timeout
    while deadline > 0:
        if predicate():
            return True
        sleep(0.02)
        deadline -= 0.02
    return False


def test_task_from_real_thread_runs_on_the_hub_thread():
    """非 hub 线程投递的任务必须回到 hub 线程执行（本测试主线程即 hub）。"""
    dispatcher = _drain(HubDispatcher())
    hub_tid = threading.get_ident()
    seen = {}

    def worker():
        seen['worker_tid'] = threading.get_ident()
        dispatcher.post(lambda: seen.update(exec_tid=threading.get_ident()))

    t = threading.Thread(target=worker)
    t.start()
    t.join(5)
    assert not t.is_alive()

    assert _wait_for(lambda: 'exec_tid' in seen), '投递的任务没有被执行'
    assert seen['exec_tid'] == hub_tid, '任务必须在 hub 线程上执行'
    assert seen['exec_tid'] != seen['worker_tid'], '不能在投递方线程上执行'


def test_tasks_are_not_serialized():
    """多段对话必须并发，不能被消费循环串行化。

    用事件同步而非计时，避免机器负载导致抖动：让 A 一直等 B 启动。
    若消费循环直接调用 `func()`，A 会占住循环直到自己结束，B 永远得不到执行，
    A 只能超时失败。修复后每个任务各是一个 greenlet，A 等待期间会让出事件循环。
    """
    dispatcher = _drain(HubDispatcher())
    b_started = threading.Event()
    seen = {}

    def task_a():
        # 模拟 stream_msg：长时间协作式等待，期间 B 必须能跑起来。
        # 留足余量（最多 5 秒），避免机器负载高时误报。
        for _ in range(250):
            if b_started.is_set():
                seen['ok'] = True
                return
            sleep(0.02)
        seen['ok'] = False

    def task_b():
        b_started.set()

    dispatcher.post(task_a)
    dispatcher.post(task_b)

    assert _wait_for(lambda: 'ok' in seen, timeout=10), '任务未被处理'
    assert seen['ok'] is True, (
        'A 等待期间 B 无法启动 —— 任务被串行化了（消费循环不应直接调用 func()）'
    )


def test_slow_task_does_not_delay_later_tasks():
    """长任务等待期间，队列里后续任务仍要被处理。

    必须用协作式 `sleep`（等同 `stream_msg` 读流时 park 自己），
    不能用 `threading.Event().wait()`：后者是**真实阻塞**，会占住整个 OS 线程，
    连消费循环都无法运行——那不是本测试要覆盖的场景。

    也不能写成「slow 睡 0.4s，然后断言 fast 已到」：那是拿固定时长跟轮询赛跑，
    机器负载高时会误报。这里让 slow **一直等** fast 完成，判据是 slow 有没有
    等到超时——若被串行化，fast 根本没有机会运行，slow 必然超时。
    """
    dispatcher = _drain(HubDispatcher())
    order = []
    fast_done = threading.Event()

    def slow():
        order.append('slow-start')
        for _ in range(250):  # 最多等 5 秒
            if fast_done.is_set():
                order.append('slow-seen-fast')
                return
            sleep(0.02)
        order.append('slow-timeout')

    dispatcher.post(slow)
    assert _wait_for(lambda: 'slow-start' in order, timeout=5), '慢任务未启动'

    def fast():
        order.append('fast')
        fast_done.set()

    dispatcher.post(fast)

    assert _wait_for(lambda: fast_done.is_set(), timeout=10), '快任务未被处理'
    assert 'slow-timeout' not in order, (
        'slow 等到了超时，说明 fast 在它等待期间无法运行 —— 任务被串行化了'
    )


def test_task_exception_does_not_stop_the_drain():
    """单个任务抛异常不能拖垮消费循环，后续任务仍要执行。"""
    dispatcher = _drain(HubDispatcher())
    ran = {}

    def boom():
        raise RuntimeError('boom')

    dispatcher.post(boom)
    dispatcher.post(lambda: ran.update(second=True))

    assert _wait_for(lambda: ran.get('second') is True), (
        '前一个任务失败导致后续任务未被处理'
    )


def test_task_exception_is_isolated_from_sibling_tasks():
    """某个任务抛异常，不能让并发执行的兄弟任务受影响。"""
    dispatcher = _drain(HubDispatcher())
    ok = {}

    def boom():
        raise RuntimeError('boom')

    def fine():
        sleep(0.05)
        ok['done'] = True

    dispatcher.post(fine)
    dispatcher.post(boom)

    assert _wait_for(lambda: ok.get('done') is True), '异常任务影响了兄弟任务'


def test_post_from_hub_thread_itself_also_works():
    """hub 自己投递也要能被执行。"""
    dispatcher = _drain(HubDispatcher())
    ran = {}

    dispatcher.post(lambda: ran.update(ok=True))

    assert _wait_for(lambda: ran.get('ok') is True)


def test_start_is_idempotent():
    """重复启动不应创建多个消费循环（否则任务会被并发抢走、顺序错乱）。"""
    dispatcher = HubDispatcher()
    dispatcher.start()
    dispatcher.start()

    assert dispatcher._started is True


def test_post_does_not_block_the_caller():
    """投递必须是「点火即走」，不能阻塞真实线程（否则又会卡住调用方）。"""
    # 刻意不启动消费循环：队列无人消费，投递仍应立刻返回
    dispatcher = HubDispatcher()
    done = threading.Event()

    def worker():
        dispatcher.post(lambda: None)
        done.set()

    t = threading.Thread(target=worker)
    t.start()
    t.join(2)

    assert done.is_set(), '投递阻塞了调用方'


# ---------------- 保序通道（ordered=True）----------------
#
# TTS 的音频分片与紧随其后的「完成」事件顺序即语义：乱序会让前端播放错乱。
# 因此新增了保序通道，与默认的并发通道并存。


def test_ordered_channel_preserves_submission_order():
    """保序通道必须严格按投递顺序执行。"""
    dispatcher = _drain(HubDispatcher(ordered=True))
    order = []

    # 每个任务都做协作式等待：并发通道下必然乱序，保序通道下必须仍是 0..19
    for i in range(20):
        dispatcher.post(lambda i=i: (sleep(0.005), order.append(i)))

    assert _wait_for(lambda: len(order) == 20), f'未全部执行: {len(order)}'
    assert order == list(range(20)), f'保序通道出现乱序: {order}'


def test_ordered_channel_serializes_tasks():
    """保序通道内任务不得并发（并发会让顺序失去意义）。"""
    dispatcher = _drain(HubDispatcher(ordered=True))
    active = {'now': 0, 'max': 0}

    def task():
        active['now'] += 1
        active['max'] = max(active['max'], active['now'])
        sleep(0.02)
        active['now'] -= 1

    for _ in range(5):
        dispatcher.post(task)

    assert _wait_for(lambda: active['max'] > 0)
    sleep(0.3)  # 给并发执行留出窗口（若真并发，max 会变成 2+）
    assert active['max'] == 1, f'保序通道出现了并发执行（max={active["max"]}）'


def test_default_channel_still_runs_concurrently():
    """默认通道必须保持并发 —— 不能为了让 TTS 保序而把 ASR 对话串行化。

    `stream_msg` 会读到整段流结束（数十秒），串行化会让一个用户的对话把其它
    用户全堵住（这是引入本模块时踩过的回归）。
    """
    dispatcher = _drain(HubDispatcher())
    active = {'now': 0, 'max': 0}

    def task():
        active['now'] += 1
        active['max'] = max(active['max'], active['now'])
        sleep(0.1)
        active['now'] -= 1

    for _ in range(3):
        dispatcher.post(task)

    assert _wait_for(lambda: active['max'] >= 2, timeout=3.0), (
        f'默认通道被串行化了（max={active["max"]}）'
    )


def test_ordered_channel_reaches_the_hub_thread():
    """保序通道同样要把任务交回 hub 线程（线程归属不因保序而改变）。"""
    dispatcher = _drain(HubDispatcher(ordered=True))
    hub_tid = threading.get_ident()
    seen = {}

    def worker():
        dispatcher.post(lambda: seen.update(tid=threading.get_ident()))

    t = threading.Thread(target=worker)
    t.start()
    t.join(2)

    assert _wait_for(lambda: 'tid' in seen), '任务未被执行'
    assert seen['tid'] == hub_tid, '保序通道没有回到 hub 线程'


def test_tts_callbacks_are_dispatched_to_hub_in_order():
    """TTS 的音频分片与完成事件必须交回 hub，且保持先后顺序。

    故障背景：这些回调来自 SDK 的 ws 线程，却直接 `socketio.emit` —— 跨线程
    使用 hub 归属的 gevent socket 会抛 Cannot switch to a different thread。
    顺序同样重要：完成事件若先到，前端会在音频播完前就收到「结束」。
    """
    from core.tts.tts_client import TTSClient

    received = []
    tts = TTSClient(on_msg=lambda data, kind: received.append((kind, data)))

    tts.on_data(b'chunk-1')
    tts.on_data(b'chunk-2')
    tts.on_complete()

    # 用确定性同步点代替 sleep（避免负载高时偶发失败）
    run_pending_hub_tasks()

    kinds = [k for k, _ in received]
    assert kinds == [0, 0, 1], f'顺序错误或数量不对: {kinds}'
    assert received[0][1] == b'chunk-1' and received[1][1] == b'chunk-2'
    assert received[2][1] == '>>[TTS] Completed'


def test_tts_error_callback_is_dispatched_to_hub():
    """TTS 错误回调同样要交回 hub（它最终会 socketio.emit）。"""
    from core.tts.tts_client import TTSClient

    errors = []
    tts = TTSClient(on_err=errors.append)

    tts.on_error('boom')
    run_pending_hub_tasks()

    assert len(errors) == 1
    assert 'boom' in str(errors[0])


def test_asr_error_callback_is_dispatched_to_hub():
    """ASR 错误回调要交回 hub 执行。

    回调来自 ASR 的 ws 线程，而处理链会读 Redis 并最终 `socketio.emit`。
    """
    from unittest.mock import MagicMock

    from core.chat.chat_mgr import ClientContext

    socketio = MagicMock()
    ctx = ClientContext('sid-asr-err', socketio)
    ctx.asr = MagicMock()
    ctx.asr._session = None
    ctx.ai = MagicMock()
    ctx.ai.user = 'user-1'

    ctx.on_asr_err(RuntimeError('asr down'))
    # 交回 hub 执行：这里同步跑一遍待处理任务
    run_pending_hub_tasks()

    assert socketio.emit.called, 'ASR 错误未最终上报（应为 emit 到前端）'


def test_hub_thread_identity_is_preserved_for_ordered_channel():
    """保序通道执行的任务必须仍在 hub 线程 —— 否则线程归属问题没有真正解决。"""
    dispatcher = _drain(HubDispatcher(ordered=True))
    hub_tid = threading.get_ident()
    tids = []
    for _ in range(3):
        dispatcher.post(lambda: tids.append(threading.get_ident()))

    assert _wait_for(lambda: len(tids) == 3)
    assert set(tids) == {hub_tid}
