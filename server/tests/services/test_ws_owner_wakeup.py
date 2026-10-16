"""跨线程唤醒与连接关闭的线程归属（#1 / #2 的回归）。

## #2 唤醒接口

把发送调度到连接所属线程后，必须**唤醒**那个线程的循环。gevent 的两个接口差别
很关键（源码见 `core/tools/ws_owner_send.py` 的注释）：`run_callback` 只把回调
追加进列表、再启动一个定时器，**不会唤醒**正空闲在 `epoll_wait` 的循环；只有
`run_callback_threadsafe` 会额外发一次 async watcher 把它叫醒。

连接线程在等待数据时正是空闲的，所以用错接口时回调要等到循环因别的原因醒来才
执行 —— 对空闲连接就是不执行，表现为「投递超时」。

## #1 关闭也要调度

`close()` 内部会发关闭帧（用同一个 gevent socket），且可能阻塞在原生发送锁上；
从别的线程直接调用会把 hub 拖住。
"""

import threading

import pytest

from tests.services._ws_wake_probe import run_probe


@pytest.fixture(scope='module')
def wake_results(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('ws_wake')
    return {
        mode: run_probe(tmp, mode)
        for mode in ('plain', 'threadsafe')
    }


def test_threadsafe_wakeup_is_prompt(wake_results):
    """用 run_callback_threadsafe 时，投递的回调必须**立即**在所属线程执行。"""
    r = wake_results['threadsafe']
    latency = float(r.get('LATENCY', '-1'))
    assert latency >= 0, (
        f"回调从未被执行（等待超时）:\n{r['_output']}"
    )
    assert latency < 0.5, (
        f"唤醒延迟 {latency:.2f}s 偏高，目标循环没有被及时叫醒\n{r['_output']}"
    )
    assert r.get('RAN_ON_OWNER') == 'True', (
        f"回调没有运行在连接所属线程上:\n{r['_output']}"
    )


def test_plain_run_callback_is_not_faster_than_threadsafe(wake_results):
    """对照：换回 `run_callback` 只会更慢（甚至不被执行）。

    实测差异：`run_callback` 约 0.3s 才执行（它只武装了回调定时器，要等循环因
    **其它**原因醒来），`run_callback_threadsafe` 立即执行（约 0.01s）。

    这里只断言「不更快」，不断言绝对延迟——绝对延迟受环境影响，而顺序关系稳定。
    真正守住接口选择的是下面的结构断言。
    """
    plain = float(wake_results['plain'].get('LATENCY', '-1'))
    threadsafe = float(wake_results['threadsafe'].get('LATENCY', '-1'))
    assert threadsafe >= 0, f"threadsafe 未执行:\n{wake_results['threadsafe']['_output']}"

    if plain < 0:
        return      # 完全不执行：差异更明显，符合预期
    assert plain >= threadsafe, (
        f'`run_callback` 竟然比 threadsafe 更快（{plain:.3f}s vs {threadsafe:.3f}s）—— '
        '前提已变，请重新评估唤醒接口的选择'
    )


def test_schedule_uses_the_threadsafe_wakeup_api():
    """结构断言：调度时必须调用 `run_callback_threadsafe`。

    比测延迟更可靠：明确锁定「用的是哪个接口」。若有人改回 `run_callback`，
    这条会直接失败并指出原因。
    """
    from types import SimpleNamespace

    from core.tools import ws_owner_send as wos

    calls = []

    class FakeLoop:
        def run_callback(self, func, *args):
            calls.append('plain')
            return None

        def run_callback_threadsafe(self, func, *args):
            calls.append('threadsafe')
            return None

    fake_hub = SimpleNamespace(loop=FakeLoop(), thread_ident=-1)   # 非当前线程
    app = SimpleNamespace(
        sock=SimpleNamespace(sock=SimpleNamespace(hub=fake_hub))
    )

    wos._state_for(app).scheduled = False      # 清掉可能残留的标记
    wos.run_on_owner(app, lambda: None)

    assert calls, '没有触发任何调度'
    assert calls[0] == 'threadsafe', (
        f"调度使用了 {calls[0]!r} —— 必须用 run_callback_threadsafe："
        'run_callback 不会唤醒空闲在 epoll 上的连接线程，发送会迟迟不落地'
    )


def test_close_is_dispatched_to_owner_thread():
    """`close_on_owner` 必须把关闭动作交给所属线程。"""
    from core.tools.ws_owner_send import close_on_owner

    class FakeApp:
        def __init__(self):
            self.closed = []
            # 不带 hub：run_on_owner 会走「同线程/无 hub 直接执行」分支
        def close(self, *a, **k):
            self.closed.append(threading.get_ident())

    app = FakeApp()
    close_on_owner(app)
    assert len(app.closed) == 1, '关闭没有被执行'
    assert app.closed[0] == threading.get_ident()


def test_close_uses_zero_timeout_to_skip_the_handshake():
    """关闭必须传 `timeout=0`，从而**不**同步接收关闭帧。

    `WebSocket.close(status, reason, timeout)` 发完关闭帧后会同步收对方的关闭帧：

        while timeout is None or time.time() - start_time < timeout:
            frame = self.recv_frame()      # ← 与 run_forever 抢同一个接收锁

    而这个调用发生在连接所属线程上，那里正有 `run_forever` 的接收循环在跑
    （可能已读到半个帧并持锁）。两个协程争抢同一个原生接收锁 → 连接线程死锁。
    传 0 后 while 条件直接为假，循环体不执行：只发关闭帧，不等握手。
    """
    from core.tools.ws_owner_send import close_on_owner

    class FakeApp:
        def __init__(self):
            self.calls = []

        def close(self, **kwargs):
            self.calls.append(kwargs)

    app = FakeApp()
    close_on_owner(app)

    assert app.calls, '关闭没有被调用'
    assert app.calls[0].get('timeout') == 0, (
        f"关闭没有传 timeout=0（实际 {app.calls[0]!r}）—— "
        '会同步等待关闭帧，与接收循环争抢原生接收锁，导致连接线程死锁'
    )


def test_close_falls_back_when_close_rejects_kwargs():
    """极老版本 websocket-client 的 close() 不接受参数时也要能关闭。"""
    from core.tools.ws_owner_send import close_on_owner

    class OldApp:
        def __init__(self):
            self.closed = 0

        def close(self):          # 不接受任何关键字参数
            self.closed += 1

    app = OldApp()
    close_on_owner(app)
    assert app.closed == 1


def test_stuck_operation_does_not_block_close():
    """一个卡住的发送不能把排在它后面的**关闭**永远挡住。

    对端不收数据时 `send` 会一直阻塞；没有执行上限的话，排在后面的关闭永远轮不到，
    队列整体卡死。这里用一个「永不返回」的动作验证后续动作仍能执行。
    """
    from types import SimpleNamespace

    from gevent import get_hub
    from gevent import sleep as gevent_sleep

    from core.tools import ws_owner_send as wos

    calls = []

    class FakeLoop:
        """真实 hub 的 loop，另记一层便于观察调度。"""

        def __init__(self, loop):
            self._loop = loop

        def run_callback(self, func, *args):
            return self._loop.run_callback(func, *args)

        def run_callback_threadsafe(self, func, *args):
            fn = getattr(self._loop, 'run_callback_threadsafe', None) or self._loop.run_callback
            return fn(func, *args)

    hub = get_hub()
    # 谎报 hub 属于别的线程，使 run_on_owner 走「入队 + 调度」分支
    fake_hub = SimpleNamespace(loop=FakeLoop(hub.loop), thread_ident=-99999)
    app = SimpleNamespace(sock=SimpleNamespace(sock=SimpleNamespace(hub=fake_hub)))

    original = wos._OPERATION_TIMEOUT
    wos._OPERATION_TIMEOUT = 0.4
    try:
        wos.run_on_owner(app, lambda: gevent_sleep(30))   # 卡住（会被超时打断）
        wos.run_on_owner(app, lambda: calls.append('after'))

        deadline = 5.0
        while deadline > 0 and 'after' not in calls:
            gevent_sleep(0.05)
            deadline -= 0.05

        assert 'after' in calls, (
            '卡住的动作把后面的动作永远挡住了 —— 队列整体卡死，关闭将无法执行'
        )
    finally:
        wos._OPERATION_TIMEOUT = original


def test_run_on_owner_alias_is_kept():
    """`send_on_owner` 旧名保留为别名，避免外部引用失效。"""
    from core.tools import ws_owner_send as wos

    assert wos.send_on_owner is wos.run_on_owner
