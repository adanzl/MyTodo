"""
异步工具函数
用于在同步代码中调用异步函数
"""
import asyncio
import threading

from gevent import Timeout as GeventTimeout
from gevent import spawn


def run_async(coroutine, timeout: float = None):
    """
    在新的事件循环中运行协程
    用于在同步代码中调用异步函数
    
    使用 gevent.spawn 在线程中运行，避免阻塞其他 gevent 协程
    
    :param coroutine: 协程对象
    :param timeout: 超时时间（秒），可选
    :return: 协程的返回值
    """

    def run_in_thread():
        """在线程中运行异步函数"""
        # 在线程中也需要应用 nest_asyncio（每个线程独立）
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except Exception:
            pass
        
        # 在线程中，必须创建完全独立的事件循环
        # 清除可能存在的任何事件循环引用
        try:
            # 清除当前线程的事件循环
            try:
                policy = asyncio.get_event_loop_policy()
                policy.set_event_loop(None)
            except Exception:
                try:
                    asyncio.set_event_loop(None)
                except Exception:
                    pass
        except Exception:
            pass
        
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 创建一个包装协程，确保在运行中的循环上下文中执行
            async def run_coroutine():
                return await coroutine
            
            # 手动实现超时，避免使用 asyncio.wait_for（它需要运行中的循环）
            if timeout:
                # 创建任务（这会确保在运行中的循环上下文中）
                task = loop.create_task(run_coroutine())
                cancelled = False
                
                def cancel_task():
                    nonlocal cancelled
                    if not task.done():
                        cancelled = True
                        task.cancel()
                
                timeout_handle = loop.call_later(timeout, cancel_task)
                
                try:
                    # 使用 run_forever 确保循环真正运行
                    result = None
                    exception = None
                    
                    def set_result(future):
                        nonlocal result, exception
                        if future.done():
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
                    
                    if cancelled:
                        raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
                    if exception:
                        raise exception
                    return result
                except asyncio.CancelledError:
                    if cancelled:
                        raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
                    raise
            else:
                # 对于没有超时的情况，也需要确保在运行中的循环上下文中
                task = loop.create_task(run_coroutine())
                result = None
                exception = None
                
                def set_result(future):
                    nonlocal result, exception
                    if future.done():
                        try:
                            result = future.result()
                        except Exception as e:
                            exception = e
                        loop.stop()
                
                task.add_done_callback(set_result)
                loop.run_forever()
                
                if exception:
                    raise exception
                return result
        finally:
            # 清理事件循环
            try:
                # 取消所有待处理的任务
                pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                if pending:
                    for task in pending:
                        if not task.done():
                            task.cancel()
                    # 等待取消完成
                    if pending:
                        try:
                            loop.run_until_complete(
                                asyncio.gather(*pending, return_exceptions=True)
                            )
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                if not loop.is_closed():
                    loop.close()
            except Exception:
                pass
            try:
                policy = asyncio.get_event_loop_policy()
                policy.set_event_loop(None)
            except Exception:
                try:
                    asyncio.set_event_loop(None)
                except Exception:
                    pass
    
    # 使用 gevent.spawn 在线程中运行
    result_container = {'result': None, 'exception': None}
    
    def thread_wrapper():
        """线程包装函数"""
        try:
            result_container['result'] = run_in_thread()
        except Exception as e:
            result_container['exception'] = e
    
    # 在线程中运行
    thread = threading.Thread(target=thread_wrapper)
    thread.start()
    
    # 使用 gevent.spawn 等待线程完成（不阻塞其他 gevent 协程）
    def wait_for_thread():
        """等待线程完成的函数"""
        thread.join()
    
    if timeout:
        try:
            with GeventTimeout(timeout + 1.0):  # 多给1秒缓冲
                greenlet = spawn(wait_for_thread)
                greenlet.join()
        except GeventTimeout:
            raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
    else:
        greenlet = spawn(wait_for_thread)
        greenlet.join()
    
    # 检查结果
    if result_container['exception']:
        raise result_container['exception']
    
    return result_container['result']

