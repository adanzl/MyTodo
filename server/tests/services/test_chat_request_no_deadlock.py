"""`chat_request_store` 不得在持原生锁时访问 Redis（死锁回归）。

故障记录（2026-10-16）：服务运行十几分钟后整个进程冻结、日志完全空白、只能重启。
`_store_lock` 在 `monkey.patch_all(thread=False)` 下是**真实**锁，而 Redis 访问会
park 协程：A 持锁等 Redis，同线程的 B 在锁上阻塞整个 OS 线程，A 永远无法被唤醒。

本测试在**独立子进程**里复现该场景并加外部超时：gevent 的 `Timeout` 无法中断对
真实锁的等待，若回归，测试进程会自己挂死而不是给出失败信息，所以超时必须在父进程。
"""

import os
import subprocess
import sys

import pytest

_SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROBE = os.path.join(_SERVER_ROOT, 'tests', 'services', '_deadlock_probe.py')

# 探针内部对每个场景设 6s 上限，4 个场景合计不应超过约 30s
_OUTER_TIMEOUT = 60


def test_store_does_not_deadlock_when_redis_is_slow(tmp_path):
    env = dict(os.environ)
    env.setdefault('PYTHONIOENCODING', 'utf-8')
    # 直接以脚本方式运行时 sys.path[0] 是脚本所在目录，需显式补上 server 根目录
    env['PYTHONPATH'] = os.pathsep.join(
        [_SERVER_ROOT, env.get('PYTHONPATH', '')]
    ).rstrip(os.pathsep)
    # 子进程不走 tests/conftest.py，自己把本地回退存储指向临时目录，
    # 否则导入 rds_mgr 时会写坏被 git 跟踪的 server/rds_local.json
    env['RDS_LOCAL_FILE'] = str(tmp_path / 'rds_probe.json')

    try:
        proc = subprocess.run(
            [sys.executable, _PROBE],
            cwd=_SERVER_ROOT,
            env=env,
            capture_output=True,
            text=True,
            errors='replace',
            timeout=_OUTER_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f'子进程超过 {_OUTER_TIMEOUT}s 未结束：持原生锁访问 Redis 的死锁回归了。'
            '（gevent 的 Timeout 无法中断真实锁等待，只能靠外部超时）'
        )

    assert proc.returncode == 0, f'探针失败:\n{proc.stdout}\n{proc.stderr}'
    assert 'NO-DEADLOCK' in proc.stdout, f'缺少成功标记:\n{proc.stdout}\n{proc.stderr}'
    # 每个场景都应打印 ok，避免"提前退出但恰好返回 0"这种假通过
    assert proc.stdout.count('[ok]') == 4, f'场景未全部执行:\n{proc.stdout}'
