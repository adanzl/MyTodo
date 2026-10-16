"""在 gevent 环境里用**一条长期存活的事件循环**执行异步任务（BLE 专用）。

## 为什么需要它

`core.tools.async_util.run_async` 的语义是「一次性」的：每次调用都新起一条线程，
在其中 `asyncio.run(coro)` —— 也就是**新建一个事件循环，跑完立刻关闭**。对一锤子
买卖的协程没问题，但 BLE 不是：

`BleakClient.connect()` 会在**当时那个事件循环**上创建 asyncio 原语
（Future / Event / transport，以及后端自己的 task）。而 `BluetoothMgr` 把这个
client 缓存在 `BluetoothDev.client` 上跨调用复用：

    connect_device            （第一次 run_async，循环 A）→ 创建 client、connect，
                                                            存进 device.client
    _get_device_name_from_gatt（同一次调用内，循环 A）→ 读 GATT，正常
    disconnect_device         （第二次 run_async，循环 B）→ 再取 device.client，
                                                            可它绑在**已关闭**的循环 A

于是第二次操作必然失败：`RuntimeError: Event loop is closed`（bleak 还可能报
"Future attached to a different loop"）。症状是「能连上，但之后再也断不开 /
读不到 GATT」。

## 修法

在一条专用守护线程里长期 `run_forever` 的循环上跑所有 BLE 协程，
`BleakClient` 的创建与使用就永远落在同一个循环。

## 与 async_util 的关系

刻意**不改** `async_util.run_async` / `wait_thread`（其它模块在用，语义就是
「每次新建循环」）。本模块只服务「循环必须长期存活」的场景。

## 等待方式（重要）

提交用 `asyncio.run_coroutine_threadsafe`，但**不用** `future.result(timeout=...)`：
`threading` 没有被 patch（`patch_all(thread=False)`），它的等待是**原生阻塞**，
会占住整个 hub（其它 HTTP/socket.io 请求全部排不上，见 async_util、
hub_dispatch 与 utils.get_media_duration 的注释）。这里改成 `future.done()` +
`gevent_sleep` 轮询，与 `run_async` / `wait_thread` 一致：hub 上的其它 greenlet
照常被调度，而超时仍然一定生效（不会无限等）。
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Coroutine, Optional, TypeVar

from gevent import sleep as gevent_sleep

from core.config import app_logger

log = app_logger

_T = TypeVar("_T")

# 轮询间隔：与 async_util 保持一致，让 hub 每 10ms 有机会调度其它 greenlet
_POLL_INTERVAL = 0.01
# 循环线程启动等待上限（只是创建 loop + 起线程，正常在毫秒级完成）
_START_TIMEOUT = 5.0
_DEFAULT_TIMEOUT = 10.0


class AsyncLoopRunner:
    """在专用守护线程里长期运行一条事件循环，供多个调用方复用。

    线程**惰性启动**：第一次 `submit` 才创建；之后所有 `submit` 都提交到同一个
    循环，因此循环上创建的对象（如 BleakClient 绑定的 asyncio 原语）可以跨调用
    安全复用。
    """

    def __init__(self, name: str = "async-loop") -> None:
        self._name = name
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._started = threading.Event()
        # threading 未被 gevent patch（thread=False），这是**真实**锁，
        # 可安全用于跨线程的一人启动
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ 状态

    @property
    def thread(self) -> Optional[threading.Thread]:
        """循环线程（未启动或已停止时为 None）。"""
        return self._thread

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """当前事件循环（未启动或已关闭时为 None）。"""
        return self._loop

    # -------------------------------------------------------------- 线程主体

    def _run_forever(self) -> None:
        """循环线程主体：建循环、跑起来、退出时收尾。"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._started.set()
        try:
            loop.run_forever()
        except BaseException as e:  # noqa: BLE001 - 守护线程不能把异常甩给解释器
            log.error(f"[AsyncLoop] 事件循环异常退出: {e}", exc_info=True)
        finally:
            self._shutdown_loop(loop)

    @staticmethod
    def _shutdown_loop(loop: asyncio.AbstractEventLoop) -> None:
        """收尾：取消仍在排队的任务，再关闭循环。"""
        try:
            pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True))
        except Exception as e:  # noqa: BLE001
            log.warning(f"[AsyncLoop] 收尾未完成任务时出错（忽略）: {e}")
        finally:
            try:
                loop.close()
            except Exception as e:  # noqa: BLE001
                log.warning(f"[AsyncLoop] 关闭事件循环出错（忽略）: {e}")

    def _ensure_started(self) -> asyncio.AbstractEventLoop:
        """惰性启动循环线程并等待循环就绪，返回该循环。"""
        loop = self._loop
        thread = self._thread
        if (loop is not None and not loop.is_closed() and thread is not None
                and thread.is_alive()):
            return loop

        with self._lock:
            # 双重检查：并发调用时只允许一个线程真正启动
            loop = self._loop
            thread = self._thread
            if (loop is not None and not loop.is_closed() and thread is not None
                    and thread.is_alive()):
                return loop

            self._started.clear()
            thread = threading.Thread(target=self._run_forever,
                                      name=self._name,
                                      daemon=True)
            self._thread = thread
            thread.start()

        # 协作式等待就绪：不能用 Event.wait()（原生阻塞会占住 hub）
        deadline = time.monotonic() + _START_TIMEOUT
        while not self._started.is_set():
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    f"事件循环线程启动超时 ({_START_TIMEOUT}s)")
            gevent_sleep(_POLL_INTERVAL)

        loop = self._loop
        if loop is None:
            raise RuntimeError("事件循环线程启动了但没有可用的循环")
        return loop

    # ------------------------------------------------------------------ 提交

    def submit(self, coroutine: Coroutine[Any, Any, _T],
               timeout: Optional[float] = None) -> _T:
        """把协程提交到本 runner 的循环并等待结果。

        - 带超时：超时会取消任务并抛 `asyncio.TimeoutError`（与
          `async_util.run_async` 的超时语义一致，调用方已有对应的 except）。
        - 协程内抛出的异常原样向上抛（同样与 `run_async` 一致）。
        - 等待期间用 gevent 协作式轮询，不阻塞 hub。
        """
        wait = timeout if timeout is not None else _DEFAULT_TIMEOUT

        if threading.current_thread() is self._thread:
            # 在循环线程内部同步等待自己会死锁，明确报错而不是挂死
            try:
                coroutine.close()
            except Exception:  # noqa: BLE001
                pass
            raise RuntimeError(
                "不能在事件循环线程内部同步提交协程（会自锁）；"
                "请在协程内部 await 目标协程")

        loop = self._ensure_started()
        future = asyncio.run_coroutine_threadsafe(coroutine, loop)

        deadline = time.monotonic() + wait
        while not future.done():
            if time.monotonic() >= deadline:
                future.cancel()
                log.warning("[AsyncLoop] 协程超时 (%ss)，已请求取消", wait)
                raise asyncio.TimeoutError(
                    f"Operation timed out after {wait} seconds")
            gevent_sleep(_POLL_INTERVAL)

        return future.result()

    # ------------------------------------------------------------------ 收尾

    def shutdown(self, timeout: float = 5.0) -> bool:
        """停止循环线程，返回是否已停止（主要给测试收尾/重启场景用）。"""
        loop = self._loop
        thread = self._thread
        if loop is None or thread is None or not thread.is_alive():
            return True

        try:
            loop.call_soon_threadsafe(loop.stop)
        except RuntimeError as e:  # 循环刚好自己停了
            log.warning(f"[AsyncLoop] 请求停止循环失败（忽略）: {e}")

        deadline = time.monotonic() + timeout
        while thread.is_alive():
            if time.monotonic() >= deadline:
                return False
            gevent_sleep(_POLL_INTERVAL)
        return True


# 进程级单例：所有「需要同一个循环」的调用方共用它
_runner = AsyncLoopRunner()


def get_runner() -> AsyncLoopRunner:
    """取得进程级 runner（测试可替换/收尾）。"""
    return _runner


def run_async_on_loop(coroutine: Coroutine[Any, Any, _T],
                      timeout: Optional[float] = None) -> _T:
    """在**共享的持久事件循环**上运行协程并等待结果（带超时）。

    与 `async_util.run_async` 的区别只有一个，但很关键：循环不随调用创建/销毁，
    因此循环上创建的对象（如 `BleakClient`）可以跨多次调用安全复用。
    """
    return _runner.submit(coroutine, timeout=timeout)
