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


def _cleanup_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """清理事件循环：取消所有待处理任务并关闭循环，释放资源"""
    try:
        pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except Exception:
        pass
    
    try:
        if not loop.is_closed():
            loop.close()
    except Exception:
        pass
    
    _clear_event_loop()


def _run_in_thread(coroutine: Coroutine, timeout: Optional[float] = None) -> Any:
    """
    在线程中运行异步函数
    
    手动管理事件循环，确保 aiohttp 等库能正确获取运行中的事件循环
    """
    _clear_event_loop()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        task = loop.create_task(coroutine)
        cancelled = False
        timeout_handle = None
        
        if timeout:
            def cancel_task() -> None:
                nonlocal cancelled
                if not task.done():
                    cancelled = True
                    task.cancel()
            timeout_handle = loop.call_later(timeout, cancel_task)
        
        # 运行任务并获取结果
        result = None
        exception = None
        
        def set_result(future: asyncio.Task) -> None:
            nonlocal result, exception
            try:
                result = future.result()
            except Exception as e:
                exception = e
            loop.stop()
        
        task.add_done_callback(set_result)
        loop.run_forever()
        
        # 取消超时回调
        if timeout_handle and not timeout_handle.cancelled():
            timeout_handle.cancel()
        
        # 处理结果
        if cancelled:
            raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
        if exception:
            raise exception
        return result
    except asyncio.CancelledError:
        if cancelled:
            raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
        raise
    finally:
        _cleanup_event_loop(loop)


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
