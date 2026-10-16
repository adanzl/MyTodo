"""`chat_request_store` 本地回退分支的 hub 冻结回归。

故障现象：Redis 不可用（回退本地 JSON）时，若干并发协程反复做
`set_phase` / `get_record`，hub **永久冻结** —— 任何请求都不再被处理。

根因：`_store_lock` 曾是原生 `threading.Lock`，而它保护的 `_load` / `_save`
并不是纯本地操作，它们走 `rds_mgr`；`rds_mgr` 在 Redis 不可用时用**自己的原生锁**
保护本地 JSON 文件，还可能做连接尝试。于是出现「持真锁 → 等真锁」：一个协程持
`_store_lock` 卡在 `rds_mgr` 里，其它协程全堵在 `_store_lock` 上；原生锁会把整个
OS 线程停住，hub 随即冻结。

实测证据（faulthandler dump）：主线程卡在 `chat_request_store.py` 的
`with _store_lock:` 这一行不动。

修复：换成 gevent 协作式可重入锁（等待时 park 自己、让出 hub；可重入避免自锁）。

探针必须跑独立子进程：卡死是「进程冻住」而不是抛异常，需要外部超时 + 看门狗判定。
看门狗用**真实线程**（`threading` 未被 patch），hub 冻住时它仍能运行。
"""

from tests.services._probe_helper import run_probe

_FREEZE_PROBE = r'''
from gevent import monkey

monkey.patch_all(subprocess=True, thread=False, queue=False)

import os
import sys
import threading
import time

from gevent import sleep, spawn

# 看门狗：真实线程，hub 被冻住时它照样能跑。
# 超过时限仍未完成 → 打印 FROZEN 并硬退出（否则进程会一直挂着）。
WATCHDOG_SECONDS = 15


def watchdog():
    time.sleep(WATCHDOG_SECONDS)
    print('FROZEN=True', flush=True)
    sys.stdout.flush()
    os._exit(9)


threading.Thread(target=watchdog, daemon=True).start()

import core.chat.chat_request_store as crs  # noqa: E402

# 强制走本地回退分支，并制造「rds 调用有延迟/带自己的锁」这一现实条件
import core.db.rds_mgr as rds  # noqa: E402

_real_get = rds.get_str
_real_set = rds.setex


def slow_get(key):
    sleep(0.01)          # 模拟网络/文件延迟（协作式）
    return _real_get(key)


def slow_set(key, ttl, value):
    sleep(0.01)
    return _real_set(key, ttl, value)


rds.get_str = slow_get
rds.setex = slow_set
crs.rds_mgr = rds
# 让 Lua 路径返回 None → 走本地回退（Redis 不可用时的真实分支）
rds.eval_lua = lambda *a, **k: None

WORKERS = 6
ROUNDS = 20
done = {'n': 0}
errors = []


def worker(idx):
    try:
        for i in range(ROUNDS):
            rid = 'rid-%d-%d' % (idx, i)
            crs.set_phase(rid, 'user-1', 'streaming')
            if crs.get_record(rid, 'user-1') is None:
                errors.append('missing %s' % rid)
                return
        done['n'] += 1
    except BaseException as e:  # noqa: BLE001
        errors.append('%s: %s' % (type(e).__name__, e))


for w in range(WORKERS):
    spawn(worker, w)

deadline = 12.0
while done['n'] < WORKERS and deadline > 0:
    sleep(0.05)
    deadline -= 0.05

print('DONE_WORKERS=%d' % done['n'], flush=True)
print('ERRORS=%s' % ('|'.join(errors[:2]) if errors else 'None'), flush=True)
print('FROZEN=False', flush=True)
print('DONE', flush=True)
sys.stdout.flush()
os._exit(0)
'''


def test_local_fallback_does_not_freeze_hub(tmp_path):
    """Redis 不可用时的并发读写不得冻结 hub（回归即进程挂死）。"""
    proc = run_probe(_FREEZE_PROBE, tmp_path, timeout=90)

    assert proc.returncode == 0, (
        f'探针未正常结束（returncode={proc.returncode}）——出现冻结:\n'
        f'{proc.stdout}\n{proc.stderr}'
    )
    assert 'FROZEN=True' not in proc.stdout, (
        f'hub 被冻结：并发读写卡在 `_store_lock` 上（原生锁 + 原生锁互等）\n'
        f'{proc.stdout}'
    )

    line = [l for l in proc.stdout.splitlines() if l.startswith('DONE_WORKERS=')]
    assert line, f'探针未产出结果:\n{proc.stdout}'
    assert int(line[0].split('=', 1)[1]) == 6, (
        f'有协程没跑完:\n{proc.stdout}'
    )
    assert 'ERRORS=None' in proc.stdout, f'读写出现错误:\n{proc.stdout}'


def test_store_lock_is_cooperative_not_native():
    """结构断言：`_store_lock` 必须是 gevent 锁，不能是原生锁。

    比跑并发探针更直接：原生锁 + 锁内访问 rds 就是「持真锁等真锁」，
    会冻结整个 OS 线程。这条能立刻拦住改回 `threading.Lock` 的提交。
    """
    from gevent.lock import RLock, Semaphore

    from core.chat import chat_request_store as crs

    lock = crs._store_lock
    assert isinstance(lock, (RLock, Semaphore)), (
        f'`_store_lock` 是 {type(lock).__name__} —— 必须是 gevent 协作式锁。'
        '原生锁在锁内访问 rds_mgr（其内部也用原生锁）会冻结整个 hub'
    )
