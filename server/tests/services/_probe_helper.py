"""hub 阻塞探针的运行助手。

`patch_all(thread=False, queue=False)` 使 `threading` / `queue` 保持**原生**实现，
因此在 greenlet 里做阻塞等待会占住整个 OS 线程（hub），其它请求全部排不上。

这类缺陷的特点是**进程挂死而不是报错**，所以必须在独立子进程里跑并加外部超时：
一旦回归，父进程超时才能判定失败。子进程内用 gevent 心跳 greenlet 计数，
直接观察 hub 是否还能被调度。
"""

import os
import subprocess
import sys

_SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_probe(source: str, tmp_path, *, timeout: int = 90) -> subprocess.CompletedProcess:
    """在独立子进程中执行探针源码。

    脚本写在 `tmp_path`（pytest 临时目录），不污染工作区。
    """
    script = os.path.join(str(tmp_path), '_probe_run.py')
    with open(script, 'w', encoding='utf-8') as f:
        f.write(source)

    env = dict(os.environ)
    env.setdefault('PYTHONIOENCODING', 'utf-8')
    env['PYTHONPATH'] = os.pathsep.join([_SERVER_ROOT, env.get('PYTHONPATH', '')]).rstrip(os.pathsep)
    # 子进程不走 tests/conftest.py，自己把本地回退存储指向临时目录，
    # 否则导入 rds_mgr 会写坏被 git 跟踪的 server/rds_local.json
    env['RDS_LOCAL_FILE'] = os.path.join(str(tmp_path), 'rds_probe.json')
    # 显式关掉 Redis：否则每次都要等 ~5 秒连接超时才回退（一批探针就是几十秒），
    # 而且结果会随「本机是否恰好跑着 Redis」而变。关掉后确定性地走本地回退。
    env['REDIS_ENABLED'] = 'false'

    return subprocess.run(
        [sys.executable, script],
        cwd=_SERVER_ROOT,
        env=env,
        capture_output=True,
        text=True,
        errors='replace',
        timeout=timeout,
    )


def probe_value(stdout: str, key: str):
    """从探针输出里取出 `KEY=值`，没有则返回 None。"""
    for line in stdout.splitlines():
        if line.startswith(key + '='):
            return line.split('=', 1)[1].strip()
    return None


def run_probe_resilient(
    source: str,
    tmp_path,
    *,
    timeout: int = 90,
    attempts: int = 3,
    max_base_gap: float = 0.1,
):
    """跑探针；若基线心跳显示**机器负载过高**则重试。

    为什么需要：这类探针用「基线心跳间隔」判断环境是否安静。机器繁忙时（例如
    CI 上并行跑多个套件、或本地同时跑两份全量测试）基线会偏大，此时测量结果
    **无法判定**——但这并不代表代码有问题。直接判失败会制造与代码无关的噪声，
    与守卫的初衷相反。

    重试若干次后仍偏大则 `skip`：此时确实得不出结论，跳过比误报更诚实。

    Returns:
        子进程结果；调用方可照常断言（基线已确认可用）。
    """
    import pytest

    last = None
    for _ in range(max(1, attempts)):
        proc = run_probe(source, tmp_path, timeout=timeout)
        last = proc
        if proc.returncode != 0:
            # 探针自身失败：与负载无关，直接交给调用方断言
            return proc
        base_raw = probe_value(proc.stdout, 'BASE_GAP')
        if base_raw is None:
            return proc
        try:
            base = float(base_raw)
        except ValueError:
            return proc
        if base < max_base_gap:
            return proc

    base_raw = probe_value(last.stdout, 'BASE_GAP') if last is not None else None
    pytest.skip(
        f'环境负载过高（基线心跳间隔 {base_raw}s），hub 探测结果无法判定；'
        f'已重试 {attempts} 次仍未获得安静基线。'
        '这不是代码失败——请单独重跑该用例。'
    )
