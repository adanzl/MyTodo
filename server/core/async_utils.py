"""
异步工具函数
用于在同步代码中调用异步函数
"""
import asyncio


def run_async(coroutine, timeout: float = None):
    """
    在新的事件循环中运行协程
    用于在同步代码中调用异步函数
    
    :param coroutine: 协程对象
    :param timeout: 超时时间（秒），可选
    :return: 协程的返回值
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if timeout:
            return loop.run_until_complete(asyncio.wait_for(coroutine, timeout=timeout))
        else:
            return loop.run_until_complete(coroutine)
    except asyncio.TimeoutError:
        raise
    finally:
        try:
            # 取消所有待处理的任务
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            loop.close()
            asyncio.set_event_loop(None)
