"""
异步工具函数
用于在同步代码中调用异步函数
"""
import asyncio
import concurrent.futures
from typing import Optional, Any, Coroutine

from gevent import Timeout as GeventTimeout
from gevent import spawn


def _clear_event_loop() -> None:
    """清除当前线程的事件循环引用，确保创建新循环前状态干净"""
    try:
        policy = asyncio.get_event_loop_policy()
        policy.set_event_loop(None)
    except Exception:
        # 降级处理：使用旧API
        try:
            asyncio.set_event_loop(None)
        except Exception:
            pass


def _run_in_thread(coroutine: Coroutine, timeout: Optional[float] = None) -> Any:
    """
    在线程中运行异步函数
    
    使用 asyncio.run() 简化代码，对于超时情况使用 asyncio.wait_for() 包装
    """
    _clear_event_loop()
    
    async def _run_coroutine():
        if timeout:
            return await asyncio.wait_for(coroutine, timeout=timeout)
        else:
            return await coroutine
    
    try:
        return asyncio.run(_run_coroutine())
    except asyncio.TimeoutError as e:
        # 重新抛出超时错误，保持错误信息一致
        raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds") from e


# 使用线程池确保每次调用都在独立线程中运行（避免 gevent 单线程环境下的冲突）
_thread_pool: Optional[concurrent.futures.ThreadPoolExecutor] = None


def _get_thread_pool() -> concurrent.futures.ThreadPoolExecutor:
    """获取全局线程池（单例模式）"""
    global _thread_pool
    if _thread_pool is None:
        # 创建线程池，最大线程数根据需求调整（默认 10 个）
        _thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10, thread_name_prefix="async_runner")
    return _thread_pool


def run_async(coroutine: Coroutine, timeout: Optional[float] = None) -> Any:
    """
    在新的事件循环中运行协程
    用于在同步代码中调用异步函数
    
    使用线程池在线程中运行，确保每次调用都在独立线程中，避免 asyncio.run() 冲突
    使用 gevent.spawn 等待线程完成，避免阻塞其他 gevent 协程
    
    :param coroutine: 协程对象
    :param timeout: 超时时间（秒），可选
    :return: 协程的返回值
    :raises asyncio.TimeoutError: 如果操作超时
    """
    thread_pool = _get_thread_pool()
    
    # 在线程池中提交任务
    future = thread_pool.submit(_run_in_thread, coroutine, timeout)
    
    def wait_for_future() -> Any:
        """等待 future 完成（在 gevent greenlet 中运行）"""
        try:
            # future.result() 会阻塞，但在 gevent.spawn 中不会阻塞其他 greenlet
            wait_timeout = (timeout + 1.0) if timeout else None
            return future.result(timeout=wait_timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
    
    # 使用 gevent.spawn 等待，避免阻塞其他 gevent 协程
    try:
        if timeout:
            with GeventTimeout(timeout + 1.0):  # 多给1秒缓冲
                result = spawn(wait_for_future).get()
        else:
            result = spawn(wait_for_future).get()
        return result
    except GeventTimeout:
        # gevent 层面的超时
        future.cancel()
        raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
    except Exception as e:
        # 直接抛出异常（包括 asyncio.TimeoutError）
        raise
