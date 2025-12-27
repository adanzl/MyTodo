"""
异步工具函数
用于在同步代码中调用异步函数
"""
import asyncio
import threading
from typing import Optional, Any, Coroutine
from queue import Queue, Empty

from gevent import Timeout as GeventTimeout
from gevent import spawn

# 使用 threading.Thread 而不是 ThreadPoolExecutor，避免与 gevent 的队列冲突
# 因为 main.py 中设置了 thread=False，threading 模块不会被 gevent patch


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


def _run_in_thread(coroutine: Coroutine, timeout: Optional[float] = None, result_queue: Queue = None, error_queue: Queue = None) -> None:
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
        result = asyncio.run(_run_coroutine())
        if result_queue is not None:
            result_queue.put(result)
    except asyncio.TimeoutError as e:
        # 重新抛出超时错误，保持错误信息一致
        timeout_error = asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
        if error_queue is not None:
            error_queue.put(timeout_error)
        else:
            raise timeout_error from e
    except Exception as e:
        if error_queue is not None:
            error_queue.put(e)
        else:
            raise


def run_async(coroutine: Coroutine, timeout: Optional[float] = None) -> Any:
    """
    在新的事件循环中运行协程
    用于在同步代码中调用异步函数
    
    使用 threading.Thread 在线程中运行，避免与 gevent 的队列冲突
    使用 gevent.spawn 等待线程完成，避免阻塞其他 gevent 协程
    
    :param coroutine: 协程对象
    :param timeout: 超时时间（秒），可选
    :return: 协程的返回值
    :raises asyncio.TimeoutError: 如果操作超时
    """
    # 使用 Queue 传递结果和异常（threading.Queue 不会被 gevent patch，因为 thread=False）
    result_queue = Queue()
    error_queue = Queue()
    
    # 创建线程并启动
    thread = threading.Thread(
        target=_run_in_thread,
        args=(coroutine, timeout, result_queue, error_queue),
        daemon=True
    )
    thread.start()
    
    def wait_for_thread() -> Any:
        """等待线程完成（在 gevent greenlet 中运行）"""
        import time
        start_time = time.time()
        wait_timeout = (timeout + 1.0) if timeout else None
        
        # 使用 gevent.sleep 轮询，避免阻塞 gevent hub
        while thread.is_alive():
            # 检查是否超时
            if wait_timeout and (time.time() - start_time) > wait_timeout:
                raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
            
            # 检查是否有错误
            try:
                error = error_queue.get_nowait()
                raise error
            except Empty:
                pass
            
            # 检查是否有结果
            try:
                return result_queue.get_nowait()
            except Empty:
                pass
            
            # 让出控制权给其他 greenlet
            from gevent import sleep
            sleep(0.01)  # 10ms 轮询间隔
        
        # 线程已完成，检查结果或错误
        try:
            error = error_queue.get_nowait()
            raise error
        except Empty:
            pass
        
        try:
            return result_queue.get_nowait()
        except Empty:
            raise RuntimeError("Thread completed but no result or error was returned")
    
    # 使用 gevent.spawn 等待，避免阻塞其他 gevent 协程
    try:
        if timeout:
            with GeventTimeout(timeout + 1.0):  # 多给1秒缓冲
                result = spawn(wait_for_thread).get()
        else:
            result = spawn(wait_for_thread).get()
        return result
    except GeventTimeout:
        raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
    except Exception as e:
        # 直接抛出异常（包括 asyncio.TimeoutError）
        raise
