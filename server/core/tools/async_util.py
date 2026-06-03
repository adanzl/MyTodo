"""
在 gevent 环境中通过原生线程执行阻塞或 asyncio 代码。

背景：
- 主进程使用 gevent（SocketIO 等），但 main.py 设置 thread=False，标准库 threading 仍是真实 OS 线程。
- threading.Queue 不会被 gevent patch，适合跨线程传递结果/异常。

选用指南：
- run_in_background：点火即走，不关心返回值（如任务状态异步写库）。
- run_blocking：纯 CPU/本地 IO（无 requests/ssl）。
- http_get_bytes：对外 HTTPS（ASSRT 等）；使用 urllib（gevent patch ssl 后可用，勿 subprocess/requests）。
- run_async：在子线程跑 asyncio 协程；主线程用 gevent 轮询等待，避免 join 卡死整个 hub（蓝牙/Mi 等）。
"""
from __future__ import annotations

import asyncio
import threading
import time
from queue import Empty, Queue
from typing import Any, Callable, Coroutine, Optional, TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from gevent import Timeout as GeventTimeout
from gevent import sleep as gevent_sleep
from gevent import spawn

from core.config import app_logger

log = app_logger
_T = TypeVar("_T")


def run_in_background(func: Callable[[], None], daemon: bool = True) -> None:
    """后台线程执行，不等待结果。"""
    threading.Thread(target=func, daemon=daemon).start()


def _clear_event_loop() -> None:
    """子线程 asyncio.run 前清掉主线程残留的事件循环引用，避免 "loop already running" 等问题。"""
    try:
        asyncio.get_event_loop_policy().set_event_loop(None)
    except Exception:
        try:
            asyncio.set_event_loop(None)
        except Exception:
            pass


def _poll_worker_thread(
    thread: threading.Thread,
    result_q: Queue,
    error_q: Queue,
    wait: float,
) -> Any:
    """与 run_async 相同：轮询队列 + gevent_sleep，避免 thread.join 卡死 hub。"""

    def poll() -> Any:
        deadline = time.time() + wait + 1.0
        while thread.is_alive():
            if time.time() > deadline:
                raise TimeoutError(f"操作超时 ({wait}s)")
            try:
                raise error_q.get_nowait()
            except Empty:
                pass
            try:
                return result_q.get_nowait()
            except Empty:
                pass
            gevent_sleep(0.01)

        try:
            raise error_q.get_nowait()
        except Empty:
            pass
        try:
            return result_q.get_nowait()
        except Empty:
            raise RuntimeError("线程结束但无返回值")

    try:
        with GeventTimeout(wait + 2.0):
            return spawn(poll).get()
    except GeventTimeout:
        raise TimeoutError(f"操作超时 ({wait}s)")


def run_blocking(func: Callable[[], _T], timeout: Optional[float] = None) -> _T:
    """原生线程执行同步阻塞调用并等待结果（hub 轮询，同 run_async）。

    注意：对外 HTTPS 请用 http_get_bytes，不要用本函数包 requests。
    """
    wait = timeout if timeout is not None else 30.0
    result_q: Queue = Queue(maxsize=1)
    error_q: Queue = Queue(maxsize=1)

    def worker() -> None:
        try:
            result_q.put(func())
        except BaseException as exc:
            error_q.put(exc)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return _poll_worker_thread(thread, result_q, error_q, wait)


def http_request_bytes(
    method: str,
    url: str,
    *,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes]:
    """对外 HTTPS GET/HEAD 等（urllib，兼容 gevent patch ssl）。"""
    req = Request(url, method=method.upper(), headers=headers or {})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read()
    except HTTPError as e:
        return int(e.code), e.read()
    except URLError as e:
        reason = str(e.reason) if getattr(e, "reason", None) else str(e)
        low = reason.lower()
        if "timed out" in low or "timeout" in low:
            raise TimeoutError(f"HTTP 请求超时 ({int(timeout)}s): {reason}") from e
        raise RuntimeError(f"HTTP 请求失败: {reason}") from e


def http_get_bytes(
    url: str,
    *,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes]:
    return http_request_bytes("GET", url, timeout=timeout, headers=headers)


def run_async(coroutine: Coroutine, timeout: Optional[float] = None) -> Any:
    """在新线程的事件循环中运行协程；主线程用 gevent 轮询等待。

    不用 thread.join：在 gevent worker 中会阻塞 hub，其它请求无法调度。
    poll + gevent_sleep(0.01) 让出 greenlet，直到子线程写入 result_q / error_q。
    """
    wait = timeout if timeout is not None else 10.0
    result_q: Queue = Queue()
    error_q: Queue = Queue()

    def worker() -> None:
        _clear_event_loop()
        try:

            async def run_coro() -> Any:
                return await asyncio.wait_for(coroutine, timeout=wait)

            result_q.put(asyncio.run(run_coro()))
        except asyncio.TimeoutError:
            error_q.put(asyncio.TimeoutError(f"Operation timed out after {wait} seconds"))
        except Exception as exc:
            error_q.put(exc)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    try:
        return _poll_worker_thread(thread, result_q, error_q, wait)
    except TimeoutError as e:
        log.warning("[async_util] 协程任务超时 (%ss)，线程仍在运行", wait)
        raise asyncio.TimeoutError(f"Operation timed out after {wait} seconds") from e
