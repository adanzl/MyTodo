"""
通用工具函数
包含异步工具函数和其他通用工具函数
"""
import asyncio
import os
from core.log_config import root_logger

log = root_logger()


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


def convert_to_http_url(url: str) -> str:
    """
    将本地文件路径转换为 HTTP URL
    :param url: 本地文件路径（如 /mnt/ext_base/audio/xxx.mp3）或已经是 HTTP URL
    :return: HTTP URL
    """
    # 如果已经是 HTTP/HTTPS URL，直接返回
    if url.startswith('http://') or url.startswith('https://'):
        return url

    # 如果是 file:// URL，提取路径
    if url.startswith('file://'):
        url = url[7:]  # 移除 file:// 前缀

    # 如果是本地绝对路径（以 / 开头），转换为 HTTP URL
    if url.startswith('/') and os.path.exists(url):
        try:
            # 动态导入以避免循环依赖
            from core.api.media_routes import get_media_url
            return get_media_url(url)
        except ImportError:
            log.warning("[Utils] Cannot import get_media_url, using original URL")
            return url

    # 其他情况直接返回（可能是相对路径或其他格式）
    return url


def format_time_str(seconds: float) -> str:
    """
    将秒数格式化为 "HH:MM:SS" 格式
    :param seconds: 秒数（可以是整数或浮点数）
    :return: "HH:MM:SS" 格式的时间字符串
    """
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def time_to_seconds(time_str: str) -> int:
    """
    将 "HH:MM:SS" 格式的时间字符串转换为秒数
    :param time_str: "HH:MM:SS" 格式的时间字符串
    :return: 秒数
    """
    parts = time_str.split(':')
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]) if len(parts) == 3 else 0