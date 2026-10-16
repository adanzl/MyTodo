"""死锁复现探针（由 test_chat_request_no_deadlock.py 在子进程中运行）。

为什么必须是独立子进程：gevent 的 `Timeout` **无法**中断对真实 `threading.Lock`
的等待（已实测：`with Timeout(3)` 包裹后进程永久冻结）。一旦回归，测试进程本身
会挂死而不是失败，所以只能靠外部超时兜底。

场景：模拟「Redis 可用但慢」——`get_str` 会 park 当前 greenlet（真实环境里
socket 读就是这样），而 `eval_lua` 返回成功值表示走 Redis 分支。

修复前：A 协程持 `_store_lock` 并在 Redis 上 park；B 协程在真实锁上阻塞**整个
OS 线程**；A 再也无法被唤醒 → 永久冻结。

退出码 0 表示未死锁；若挂住则不会有输出，由父进程超时判定失败。
"""

import json
import sys

from gevent import monkey

monkey.patch_all(subprocess=True, thread=False, queue=False)

from gevent import Timeout, sleep, spawn  # noqa: E402

import core.chat.chat_request_store as store  # noqa: E402
import core.db.rds_mgr as rds_mgr  # noqa: E402

SLOW = 0.3
TIMEOUT = 6.0


def _install_slow_redis():
    """让 Redis 操作 park，同时表明 Redis 分支可用（eval_lua 非 None）。"""
    def slow_get_str(key):
        sleep(SLOW)
        return json.dumps({'phase': 'ai', 'attempt': 0})

    def slow_setex(key, ttl, value):
        sleep(SLOW)
        return True

    store.rds_mgr = rds_mgr
    rds_mgr.get_str = slow_get_str
    rds_mgr.setex = slow_setex
    rds_mgr.eval_lua = lambda *a, **k: 1


def _concurrent(call, label):
    """两个协程并发调用同一入口；若入口持锁等 Redis，这里就会冻住。"""
    g1 = spawn(call)
    sleep(0.05)  # 让 g1 先进入临界区
    g2 = spawn(call)
    sleep(0.05)
    with Timeout(TIMEOUT):
        g1.join()
        g2.join()
    print(f'  [ok] {label}')


def main() -> int:
    _install_slow_redis()

    _concurrent(lambda: store.get_record('leo', 'rid-1'), 'get_record 并发读取')
    _concurrent(
        lambda: store.append_reply_text('leo', 'rid-2', 'chunk', 0),
        'append_reply_text 并发追加',
    )
    _concurrent(
        lambda: store.mark_done('leo', 'rid-3', 0),
        'mark_done 并发完成',
    )
    _concurrent(
        lambda: store.set_phase('leo', 'rid-4', 'ai'),
        'set_phase 并发写 phase',
    )

    print('NO-DEADLOCK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
