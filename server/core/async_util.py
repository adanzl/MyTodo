"""
异步工具函数
用于在同步代码中调用异步函数
"""
import asyncio
import threading
from typing import Optional, Any, Coroutine

from gevent import Timeout as GeventTimeout
from gevent import spawn


def _clear_event_loop() -> None:
    """清除当前线程的事件循环"""
    try:
        policy = asyncio.get_event_loop_policy()
        policy.set_event_loop(None)
    except Exception:
        try:
            asyncio.set_event_loop(None)
        except Exception:
            pass


def _cleanup_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """清理事件循环：取消所有待处理任务并关闭循环"""
    try:
        # 取消所有待处理的任务
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
    """在线程中运行异步函数"""
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


def run_async(coroutine: Coroutine, timeout: Optional[float] = None) -> Any:
    """
    在新的事件循环中运行协程
    用于在同步代码中调用异步函数
    
    使用 gevent.spawn 在线程中运行，避免阻塞其他 gevent 协程
    
    :param coroutine: 协程对象
    :param timeout: 超时时间（秒），可选
    :return: 协程的返回值
    :raises asyncio.TimeoutError: 如果操作超时
    """
    result_container: dict[str, Any] = {'result': None, 'exception': None}
    
    def thread_wrapper() -> None:
        try:
            result_container['result'] = _run_in_thread(coroutine, timeout)
        except Exception as e:
            result_container['exception'] = e
    
    thread = threading.Thread(target=thread_wrapper)
    thread.start()
    
    def wait_for_thread() -> None:
        thread.join()
    
    try:
        if timeout:
            with GeventTimeout(timeout + 1.0):  # 多给1秒缓冲
                spawn(wait_for_thread).join()
        else:
            spawn(wait_for_thread).join()
    except GeventTimeout:
        raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
    
    if result_container['exception']:
        raise result_container['exception']
    
    return result_container['result']
