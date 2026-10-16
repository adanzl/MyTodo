"""ASR 回调必须交回 hub 执行。

真实故障（2026-10-16）：`aliyun_asr_client` 用
`threading.Thread(target=self.ws.run_forever)` 驱动 WebSocket，所以 `on_result`
在**真实 OS 线程**上触发。原实现直接在回调里做 Redis 读写、`socketio.emit`、
发起 `requests` 流式请求——这些对象都归属 hub，跨线程使用会抛
"Cannot switch to a different thread" 并污染连接池。

本测试锁住不变量：从非 hub 线程调用时不立即执行重活，而是投递回 hub。
"""

import threading

from gevent import sleep

from core.chat.chat_mgr import ClientContext
from core.tools import hub_dispatch


class _Recorder(ClientContext):
    """只记录是否被调用，不碰真实依赖。"""

    def __init__(self):
        pass

    def _handle_asr_result(self, text, client_request_id):  # type: ignore[override]
        _RECORD.append((threading.get_ident(), text, client_request_id))


_RECORD = []


def _fresh_drain():
    """确保进程级 dispatcher 的消费循环在运行并清空遗留任务。

    本文件只验证"是否交回 hub"，不涉及并发/串行，所以不需要隔离实例：
    任务由哪个消费循环执行都同样落在 hub 线程上。
    """
    while True:
        try:
            hub_dispatch._dispatcher._queue.get_nowait()
        except Exception:  # noqa: BLE001
            break
    hub_dispatch.start_hub_drain()
    sleep(0.05)


def _wait_for(predicate, timeout=5.0):
    deadline = timeout
    while deadline > 0:
        if predicate():
            return True
        sleep(0.02)
        deadline -= 0.02
    return False


def test_asr_result_from_real_thread_is_deferred_to_hub():
    """真实线程触发时不得就地执行，必须在 hub 线程上完成。"""
    _fresh_drain()
    _RECORD.clear()
    hub_tid = threading.get_ident()
    mgr = _Recorder()

    worker_tid = {}

    def worker():
        worker_tid['tid'] = threading.get_ident()
        mgr.on_asr_result('你好', 'rid-1')

    t = threading.Thread(target=worker)
    t.start()
    t.join(5)
    assert not t.is_alive()

    # 关键：调用返回时**不能**已经在 worker 线程上执行过
    assert _RECORD == [], 'ASR 结果不得在真实线程上就地处理'

    assert _wait_for(lambda: len(_RECORD) == 1), 'ASR 结果没有被投递到 hub'
    exec_tid, text, rid = _RECORD[0]
    assert exec_tid == hub_tid
    assert exec_tid != worker_tid['tid']
    assert (text, rid) == ('你好', 'rid-1')


def test_asr_result_on_hub_thread_runs_inline():
    """已在 hub 上时不必绕一圈队列，直接执行（保持原有同步语义）。"""
    _fresh_drain()
    _RECORD.clear()
    mgr = _Recorder()

    mgr.on_asr_result('在的', 'rid-2')

    assert len(_RECORD) == 1, 'hub 上应同步执行'
    assert _RECORD[0][0] == threading.get_ident()


def test_empty_asr_result_is_ignored():
    _fresh_drain()
    _RECORD.clear()
    mgr = _Recorder()

    mgr.on_asr_result('', 'rid-3')
    mgr.on_asr_result('有文本没 id', '')

    assert _RECORD == []
