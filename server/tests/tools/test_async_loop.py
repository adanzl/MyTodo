"""`core.tools.async_loop` 的单元测试：持久事件循环运行器。

守护的约束（回归即失败）：
1. 循环只在**一条**专用守护线程里建一次，多个调用方复用（不再是「每次新建」）；
2. 提交带超时，超时要如实抛 `asyncio.TimeoutError` 并取消任务，不能无限等；
3. 等待期间必须让出 hub（用 gevent 协作式轮询，而不是原生阻塞的
   `future.result(timeout=...)`）；
4. 在循环线程内部同步提交要**明确报错**而不是把自己锁死。
"""

import asyncio
import threading
import time

import pytest

from core.tools.async_loop import (
    AsyncLoopRunner,
    get_runner,
    run_async_on_loop,
)

# 远大于任何合理等待的时长：用来验证「不会无限等」
_FOREVER = 30.0


async def _current_loop():
    """返回协程实际运行所在的事件循环。"""
    return asyncio.get_running_loop()


async def _boom():
    raise ValueError("boom")


def test_concurrent_first_use_starts_exactly_one_loop(monkeypatch):
    """并发首次使用时，只能创建**一个**事件循环（即一个循环线程）。

    曾经有竞态：判断条件是「`self._loop` 为 None 就新建线程」，而 `_loop` 是在
    线程启动**之后**才在 `_run_forever` 里赋值的。于是当第一个调用者已经起了
    线程、但循环还没赋值时，第二个调用者会看到 `_loop is None` 并再起一个线程
    ——两个循环同时存在，调用在两者间来回切换；而 bleak 的 client 绑定在其中一个
    上，行为随即不可预期。

    断言的是 `new_event_loop` 的**调用次数**，而不是各调用者返回的 loop 身份：
    后者在竞态下会被 `self._loop` 的覆盖掩盖（大家都读到同一个最后写入的值），
    测不出「确实建了多个循环」。

    这里把「建循环」这一步人为拉长，使竞态窗口必然被命中。
    """
    real_new_loop = asyncio.new_event_loop
    created = []

    def slow_new_loop():
        time.sleep(0.3)      # 拉宽竞态窗口：让并发调用者都挤进启动阶段
        loop = real_new_loop()
        created.append(loop)
        return loop

    monkeypatch.setattr(asyncio, 'new_event_loop', slow_new_loop)

    runner = AsyncLoopRunner(name="async-loop-test-race")
    try:
        errors = []
        barrier = threading.Barrier(8)

        def worker():
            try:
                barrier.wait(timeout=10)
                runner._ensure_started()
            except BaseException as e:  # noqa: BLE001
                errors.append(f'{type(e).__name__}: {e}')

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(20)
        for t in threads:
            assert not t.is_alive(), '有调用者卡住了'

        assert not errors, f'并发启动出错: {errors}'
        assert len(created) == 1, (
            f'并发首次使用创建了 {len(created)} 个事件循环 —— '
            'BleakClient 绑定在不同循环上会行为不可预期（旧实现在此会创建多个）'
        )
    finally:
        runner.shutdown()


def test_runner_is_lazy_and_runs_in_a_daemon_thread():
    """线程惰性启动、是守护线程，且不是调用方线程。"""
    runner = AsyncLoopRunner(name="async-loop-test-lazy")
    try:
        assert runner.thread is None, "未提交任务前不应该启动线程"
        assert runner.loop is None

        loop = runner.submit(_current_loop(), timeout=5.0)

        assert runner.thread is not None
        assert runner.thread.daemon is True, "循环线程必须是守护线程，不能拦住进程退出"
        assert runner.thread.is_alive()
        assert runner.thread is not threading.current_thread()
        assert loop is runner.loop
        assert not loop.is_closed()
    finally:
        assert runner.shutdown(timeout=5.0) is True


def test_all_submits_share_one_loop():
    """多次提交必须落在同一个循环上（这正是 BLE 修复的核心）。"""
    runner = AsyncLoopRunner(name="async-loop-test-shared")
    try:
        first = runner.submit(_current_loop(), timeout=5.0)
        second = runner.submit(_current_loop(), timeout=5.0)
        third = runner.submit(_current_loop(), timeout=5.0)

        assert first is second is third, "每次提交拿到了不同的循环"
        assert not first.is_closed()
        assert first.is_running()
    finally:
        assert runner.shutdown(timeout=5.0) is True


def test_coroutine_can_await_between_submits():
    """同一循环上创建的原语（Future）跨提交复用不会炸 —— 与 BleakClient 同源。"""
    runner = AsyncLoopRunner(name="async-loop-test-primitive")
    try:

        async def create_gate():
            loop = asyncio.get_running_loop()
            gate = loop.create_future()
            loop.call_soon(gate.set_result, "ready")
            return gate

        async def wait_gate(gate):
            assert asyncio.get_running_loop() is gate.get_loop()
            return await gate

        gate = runner.submit(create_gate(), timeout=5.0)
        assert runner.submit(wait_gate(gate), timeout=5.0) == "ready"
    finally:
        assert runner.shutdown(timeout=5.0) is True


def test_timeout_raises_and_cancels_without_poisoning_the_loop():
    """超时必须如实抛 asyncio.TimeoutError，且循环随后仍可正常使用。"""
    runner = AsyncLoopRunner(name="async-loop-test-timeout")
    try:
        cancelled = threading.Event()

        async def hang():
            try:
                await asyncio.sleep(_FOREVER)
            except asyncio.CancelledError:
                cancelled.set()
                raise
            return "never"  # pragma: no cover - 不该跑到

        t0 = time.monotonic()
        with pytest.raises(asyncio.TimeoutError):
            runner.submit(hang(), timeout=0.3)
        elapsed = time.monotonic() - t0

        assert elapsed < 5.0, f"超时没有及时生效（耗时 {elapsed:.2f}s）"
        # 取消要真的送达，而不是留下一个永远跑着的任务
        loop = runner.loop
        assert loop is not None and not loop.is_closed()
        deadline = time.monotonic() + 5.0
        while not cancelled.is_set() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert cancelled.is_set(), "超时后没有往协程里投递取消"

        # 循环没被污染，仍能正常跑协程
        assert runner.submit(_current_loop(), timeout=5.0) is loop
    finally:
        assert runner.shutdown(timeout=5.0) is True


def test_coroutine_exception_propagates_like_run_async():
    """协程内部异常原样上抛（与 async_util.run_async 语义一致）。"""
    runner = AsyncLoopRunner(name="async-loop-test-exc")
    try:
        with pytest.raises(ValueError, match="boom"):
            runner.submit(_boom(), timeout=5.0)
        # 异常之后循环仍然可用
        assert runner.submit(_current_loop(), timeout=5.0) is runner.loop
    finally:
        assert runner.shutdown(timeout=5.0) is True


def test_module_level_helper_uses_the_shared_singleton():
    """模块级入口与 BLE 用的是同一个 runner（否则 client 又会跨循环）。"""
    loop = run_async_on_loop(_current_loop(), timeout=5.0)
    assert loop is get_runner().loop
    assert get_runner().thread is not None and get_runner().thread.daemon is True


def test_submit_from_loop_thread_raises_instead_of_deadlocking():
    """在循环线程内部同步提交会自锁：必须报错，并且要立刻返回。"""
    observed = {}

    async def reentrant():
        t0 = time.monotonic()
        with pytest.raises(RuntimeError, match="不能在事件循环线程内部"):
            run_async_on_loop(asyncio.sleep(0), timeout=1.0)
        observed["elapsed"] = time.monotonic() - t0
        return "ok"

    t0 = time.monotonic()
    assert run_async_on_loop(reentrant(), timeout=10.0) == "ok"
    assert time.monotonic() - t0 < 5.0, "自锁保护没有生效，等待太久了"
    assert observed["elapsed"] < 1.0


def test_shutdown_stops_the_thread_and_runner_can_restart():
    """收尾要真的停掉线程并关闭循环；之后再提交要能重新启动（不是永久失效）。"""
    runner = AsyncLoopRunner(name="async-loop-test-restart")
    try:
        first = runner.submit(_current_loop(), timeout=5.0)
        assert runner.shutdown(timeout=5.0) is True
        assert first.is_closed()
        assert runner.thread is not None and not runner.thread.is_alive()

        second = runner.submit(_current_loop(), timeout=5.0)
        assert second is not first
        assert not second.is_closed()
    finally:
        runner.shutdown(timeout=5.0)
