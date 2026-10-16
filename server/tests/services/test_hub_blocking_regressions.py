"""hub 阻塞回归测试：播放列表保存、媒体时长等待、TTS 任务停止。

对应 2026-10-16 全面扫描发现的 P1 项。共同点是它们都会在 hub 的 greenlet 里做
**原生阻塞等待**，把整个 OS 线程占住，其它请求（含 /health 与 /api/getAllUser）
全部排不上。

每个用例在独立子进程里跑并加外部超时：这类缺陷进程会挂死而非报错。
"""

import textwrap
import threading

from core.services.tools.tts_mgr import TTSMgr
from tests.services._probe_helper import run_probe, run_probe_resilient

# 子进程探针的公共头部：patch、心跳与「证人」设施。
#
# 注意：不要用「调用期间测心跳」来判断一次性阻塞。hub 被阻塞时，测量代码本身也
# 排不上队——等它终于执行时阻塞早已结束，会永远测出「健康」。
# 正确做法是让证人 greenlet 持续记录时间戳，调用返回后回看**调用窗口内的最大
# 间隔**：hub 被卡住多久，间隔就有多长。
_HEADER = textwrap.dedent("""
    from gevent import monkey
    monkey.patch_all(subprocess=True, thread=False, queue=False)

    import threading, time
    from gevent import sleep, spawn

    witness = []
    def witness_loop():
        while True:
            witness.append(time.monotonic())
            sleep(0.01)
    spawn(witness_loop)
    sleep(0.3)

    def max_gap_between(t0, t1):
        # 返回 [t0, t1] 窗口内相邻心跳的最大间隔（秒）。
        # hub 若被阻塞，窗口内几乎没有心跳，最大间隔≈阻塞时长。
        ticks = [t for t in witness if t0 <= t <= t1]
        if len(ticks) < 2:
            return t1 - t0
        return max(b - a for a, b in zip(ticks, ticks[1:]))

    def measure_call(fn):
        # 执行 fn，返回 (耗时, 窗口内最大心跳间隔)。
        t0 = time.monotonic()
        fn()
        t1 = time.monotonic()
        return t1 - t0, max_gap_between(t0, t1)

    now = time.monotonic()
    BASE = max_gap_between(now - 1.0, now)
    print('BASE_GAP=%.4f' % BASE)
""")


def _probe_value(proc, key):
    """从探针输出里取出 `KEY=值` 行。"""
    line = [l for l in proc.stdout.splitlines() if l.startswith(key + '=')]
    assert line, f'探针未产出 {key}:\n{proc.stdout}\n{proc.stderr}'
    return line[0].split('=', 1)[1]


def _assert_hub_healthy(proc, label, *, max_gap=0.25):
    """断言调用窗口内 hub 没有被长时间占据。

    判据是**最大心跳间隔**：正常运行时约 0.01s（心跳周期），
    若某处做了原生阻塞等待，该间隔会接近阻塞时长。
    """
    assert proc.returncode == 0, f'{label} 探针失败:\n{proc.stdout}\n{proc.stderr}'
    base = float(_probe_value(proc, 'BASE_GAP'))
    gap = float(_probe_value(proc, 'MAX_GAP'))
    assert base < 0.1, f'{label} 基线本身异常（{base:.3f}s），环境负载过高，无法判定'
    assert gap <= max_gap, (
        f'{label}: hub 被阻塞了约 {gap:.2f}s（正常应 ~{base:.3f}s）。'
        '原生阻塞等待会占住整个 OS 线程，其它请求全部排不上。'
    )


def test_playlist_save_worker_does_not_block_hub(tmp_path):
    """保存 worker 空闲时不得阻塞 hub。

    原实现用 `queue.Queue.get(timeout=1.0)`，而 `queue` 未被 patch：
    空闲时反复进入 1 秒的真实等待，实测把心跳拖到基线的十分之一。

    这里 worker 是**长驻**的，所以用调用窗口内的最大间隔就能看出问题
    （它会持续占住 hub）。
    """
    src = _HEADER + textwrap.dedent("""
        import core.services.playlist.repository as repo

        # 构造一个只要队列、不碰真实存储的实例
        class FakeRepo(repo.PlaylistRepository):
            def __init__(self):
                import queue
                self.rds_save_queue = queue.Queue()
                self._save_greenlet = None
                self.saved = 0
            def save(self, swallow_errors=False):
                self.saved += 1

        r = FakeRepo()
        r.start_save_worker()
        sleep(0.3)

        # 观察 2 秒：worker 若阻塞等待，这段窗口里几乎不会有心跳
        t0 = time.monotonic()
        sleep(2.0)
        t1 = time.monotonic()
        print('MAX_GAP=%.4f' % max_gap_between(t0, t1))
        print('DONE')
    """)
    # 用带负载重试的运行器：机器繁忙时基线会偏大，此时测量无法判定
    proc = run_probe_resilient(src, tmp_path, timeout=90)
    # worker 每次阻塞 1 秒，故阈值取 0.5s 以内
    _assert_hub_healthy(proc, '播放列表保存 worker', max_gap=0.5)


def test_playlist_save_worker_still_saves(tmp_path):
    """改协作等待后，投递的保存信号仍要生效（不能只修性能而丢掉功能）。"""
    src = _HEADER + textwrap.dedent("""
        import core.services.playlist.repository as repo

        class FakeRepo(repo.PlaylistRepository):
            def __init__(self):
                import queue
                self.rds_save_queue = queue.Queue()
                self._save_greenlet = None
                self.saved = 0
            def save(self, swallow_errors=False):
                self.saved += 1

        r = FakeRepo()
        r.start_save_worker()
        sleep(0.2)
        r.rds_save_queue.put('please-save')
        deadline = 5.0
        while r.saved == 0 and deadline > 0:
            sleep(0.05); deadline -= 0.05
        print('SAVED=%d' % r.saved)
        print('DONE')
    """)
    proc = run_probe(src, tmp_path, timeout=90)
    assert proc.returncode == 0, f'探针失败:\n{proc.stdout}\n{proc.stderr}'
    assert int(_probe_value(proc, 'SAVED')) >= 1, f'保存信号未被处理:\n{proc.stdout}'


def test_media_duration_does_not_block_hub(tmp_path):
    """`get_media_duration` 等待子线程时不得阻塞 hub。

    原实现 `thread.join(timeout=55)`：实测把 hub 完全占住。
    这里刻意探**真实函数**而不是 `wait_thread` 本身 —— 否则把 utils.py 改回
    `thread.join()` 也测不出来。
    `os.system` 被替换成 sleep，避免真的启动 ffprobe。

    注意用「证人间隔」而非「期间测心跳」：hub 被卡住时测量代码自己也排不上队，
    等它执行时阻塞已结束，会永远测出健康。
    """
    src = _HEADER + textwrap.dedent("""
        import core.utils as utils

        # 让「ffprobe 命令」耗时 2 秒，且不真的起进程
        def slow_system(cmd):
            time.sleep(2.0)
            return 0
        utils.os.system = slow_system

        elapsed, gap = measure_call(
            lambda: utils.get_media_duration('/tmp/whatever.mp3')
        )
        print('ELAPSED=%.3f' % elapsed)
        print('MAX_GAP=%.4f' % gap)
        print('DONE')
    """)
    # 同上：负载下基线偏大时重试或跳过，避免与代码无关的偶发失败
    proc = run_probe_resilient(src, tmp_path, timeout=90)
    assert proc.returncode == 0, f'媒体时长探针失败:\n{proc.stdout}\n{proc.stderr}'
    # 先确认"等待"确实发生过，否则这条用例可能因为没等而假通过
    assert float(_probe_value(proc, 'ELAPSED')) >= 1.5, (
        f'调用没有真的等待 2 秒，用例失去意义:\n{proc.stdout}'
    )
    _assert_hub_healthy(proc, '媒体时长等待', max_gap=0.25)


def test_wait_thread_reports_timeout(tmp_path):
    """wait_thread 超时要如实返回 False，不能假装线程已结束。"""
    src = _HEADER + textwrap.dedent("""
        import threading
        from core.tools.async_util import wait_thread

        def forever():
            time.sleep(30)
        t = threading.Thread(target=forever, daemon=True)
        t.start()

        ok = wait_thread(t, timeout=0.5)
        print('RESULT=%s' % ok)
        print('ELAPSED_OK=%s' % (not t.is_alive() or ok is False))
        print('DONE')
    """)
    proc = run_probe(src, tmp_path, timeout=90)
    assert proc.returncode == 0, f'探针失败:\n{proc.stdout}\n{proc.stderr}'
    result = [l for l in proc.stdout.splitlines() if l.startswith('RESULT=')]
    assert result and result[0].endswith('False'), f'超时应返回 False:\n{proc.stdout}'


def _fake_tts_self():
    """构造一个只含 _update_task_status* 所需依赖的最小 self。"""
    from readerwriterlock import rwlock

    class FakeTask:
        def __init__(self):
            self.status = 'processing'
            self.error_message = None

    class FakeSelf:
        def __init__(self):
            self._task_lock = rwlock.RWLockFair()
            self._task = FakeTask()
            self.saved = 0

        def _get_task(self, task_id):
            return self._task

        def _save_task_and_update_time(self, task):
            self.saved += 1

    fs = FakeSelf()
    fs._update_task_status_locked = TTSMgr._update_task_status_locked.__get__(fs)
    fs._update_task_status = TTSMgr._update_task_status.__get__(fs)
    return fs


def test_locked_variant_is_safe_while_holding_the_write_lock():
    """持有写锁时调用 `_locked` 变体必须正常完成（这正是修复点）。"""
    fs = _fake_tts_self()
    error = {}
    done = threading.Event()

    def call():
        try:
            with fs._task_lock.gen_wlock():
                fs._update_task_status_locked('t1', 'failed', '任务已被用户停止')
        except BaseException as e:  # noqa: BLE001
            error['e'] = repr(e)
        finally:
            done.set()

    t = threading.Thread(target=call, daemon=True)
    t.start()
    t.join(5)

    assert done.is_set(), '_locked 变体在持锁时阻塞了（应不取锁）'
    assert not error, f'抛出异常: {error}'
    assert fs._task.status == 'failed'
    assert fs._task.error_message == '任务已被用户停止'


def test_plain_variant_would_deadlock_while_holding_the_lock():
    """对照实验：持锁时调用**非** _locked 变体会死锁 —— 所以必须区分两个入口。

    这条守住的是"为什么不能图省事直接调 `_update_task_status`"这个约束；
    若哪天有人把它改回可重入，本用例会失败并提示重新评估。
    """
    fs = _fake_tts_self()
    done = threading.Event()

    def call():
        with fs._task_lock.gen_wlock():
            fs._update_task_status('t1', 'failed', 'x')   # 内部再取写锁
        done.set()

    t = threading.Thread(target=call, daemon=True)
    t.start()
    t.join(2)

    assert not done.is_set(), (
        '前提不成立：锁竟然可重入，那两个入口的区分就没有必要了'
    )


def test_tts_mgr_uses_locked_variant_in_the_stop_branch():
    """停止异常分支必须调用 `_locked` 变体，不能再进会取锁的实现。"""
    import inspect

    src = inspect.getsource(TTSMgr)
    # 该分支的特征：在持锁块内更新为「任务已被用户停止」
    marker = "'任务已被用户停止'"
    assert marker in src
    for line in src.splitlines():
        if marker in line and '_update_task_status' in line:
            assert '_update_task_status_locked' in line, (
                f'停止分支仍在持锁状态下调用会取锁的实现: {line.strip()}'
            )
            return
    raise AssertionError('未找到停止分支的状态更新调用，测试需要更新')
