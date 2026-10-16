"""`hub_dispatch` 的跨线程投递测试。

真实故障（2026-10-16）：ASR 的 ws 回调运行在真实 OS 线程，却直接做 Redis 读写、
`socketio.emit`、发起 `requests` 流式请求——这些都是 hub 归属对象。要么抛
"Cannot switch to a different thread"，要么污染连接池。

这里锁住核心不变量：**投递的函数最终在启动消费循环的那个线程上执行**，
而不是投递方线程（`gevent.spawn` 做不到这点，它只是新建 greenlet）。
"""

import queue
import threading

from gevent import sleep

from core.tools import hub_dispatch


def _fresh_drain():
    """清空队列并重启消费循环，保证用例相互独立。"""
    hub_dispatch._drain_started = False
    while True:
        try:
            hub_dispatch._hub_queue.get_nowait()
        except queue.Empty:
            break
    hub_dispatch.start_hub_drain()


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
    _fresh_drain()
    hub_tid = threading.get_ident()
    seen = {}

    def worker():
        seen['worker_tid'] = threading.get_ident()
        hub_dispatch.post_to_hub(
            lambda: seen.update(exec_tid=threading.get_ident())
        )

    t = threading.Thread(target=worker)
    t.start()
    t.join(5)
    assert not t.is_alive()

    assert _wait_for(lambda: 'exec_tid' in seen), '投递的任务没有被执行'
    assert seen['exec_tid'] == hub_tid, '任务必须在 hub 线程上执行'
    assert seen['exec_tid'] != seen['worker_tid'], '不能在投递方线程上执行'


def test_task_exception_does_not_stop_the_drain():
    """单个任务抛异常不能拖垮消费循环，后续任务仍要执行。"""
    _fresh_drain()
    ran = {}

    def boom():
        raise RuntimeError('boom')

    hub_dispatch.post_to_hub(boom)
    hub_dispatch.post_to_hub(lambda: ran.update(second=True))

    assert _wait_for(lambda: ran.get('second') is True), (
        '前一个任务失败导致后续任务未被处理'
    )


def test_post_from_hub_thread_itself_also_works():
    """hub 自己投递也要能被执行。"""
    _fresh_drain()
    ran = {}

    hub_dispatch.post_to_hub(lambda: ran.update(ok=True))

    assert _wait_for(lambda: ran.get('ok') is True)


def test_start_is_idempotent():
    """重复启动不应创建多个消费循环（否则任务会被并发抢走、顺序错乱）。"""
    _fresh_drain()
    hub_dispatch.start_hub_drain()

    assert hub_dispatch._drain_started is True


def test_post_does_not_block_the_caller():
    """投递必须是「点火即走」，不能阻塞真实线程（否则又会卡住调用方）。"""
    _fresh_drain()
    # 刻意不启动消费循环，队列无人消费；投递仍应立刻返回
    hub_dispatch._drain_started = False

    done = threading.Event()

    def worker():
        hub_dispatch.post_to_hub(lambda: None)
        done.set()

    t = threading.Thread(target=worker)
    t.start()
    t.join(2)

    assert done.is_set(), '投递阻塞了调用方'
