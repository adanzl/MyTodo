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

from core.tools.hub_dispatch import HubDispatcher


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
