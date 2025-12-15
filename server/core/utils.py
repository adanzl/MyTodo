"""
通用工具函数
包含异步工具函数和其他通用工具函数
"""
import asyncio
import concurrent.futures
import os
import subprocess
import threading
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
from typing import Optional, Tuple
from core.log_config import root_logger

log = root_logger()


def ok_response(data=None):
    """
    返回成功响应
    :param data: 响应数据，可选
    :return: 成功响应字典
    """
    return {"code": 0, "msg": "ok", "data": data}


def err_response(message: str):
    """
    返回错误响应
    :param message: 错误消息
    :return: 错误响应字典
    """
    return {"code": -1, "msg": message}


# 为了保持向后兼容，提供别名
_ok = ok_response
_err = err_response


def run_async(coroutine, timeout: float = None):
    """
    在新的事件循环中运行协程
    用于在同步代码中调用异步函数
    
    注意：在 gevent web 环境下，总是有运行中的事件循环，所以必须在独立线程中执行。
    由于设置了 thread=False，ThreadPoolExecutor 会使用真正的操作系统线程，每个线程有独立的事件循环上下文。
    
    :param coroutine: 协程对象
    :param timeout: 超时时间（秒），可选
    :return: 协程的返回值
    """
    def run_in_thread():
        # 在线程中，完全清除事件循环引用，然后创建新的事件循环
        # 这是关键：确保当前线程没有任何事件循环引用
        try:
            # 清除可能存在的任何事件循环引用
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
        
        # 尝试使用 asyncio.run() 如果可用（Python 3.7+）
        # 它会自动处理事件循环的创建和清理
        # 注意：不使用 asyncio.wait_for()，因为它可能检测到运行中的循环
        try:
            if hasattr(asyncio, 'run'):
                # Python 3.7+ 有 asyncio.run()
                if timeout:
                    # 手动实现超时，不使用 wait_for
                    # 注意：在 asyncio.run() 内部，我们可以安全地使用 get_running_loop()
                    async def run_with_timeout():
                        task = asyncio.create_task(coroutine)
                        cancelled = False
                        
                        def cancel_task():
                            nonlocal cancelled
                            if not task.done():
                                cancelled = True
                                task.cancel()
                        
                        # 在 asyncio.run() 创建的循环中，get_running_loop() 是安全的
                        try:
                            loop = asyncio.get_running_loop()
                            timeout_handle = loop.call_later(timeout, cancel_task)
                        except RuntimeError:
                            # 如果没有运行中的循环，直接运行任务
                            return await task
                        
                        try:
                            result = await task
                            if timeout_handle and not timeout_handle.cancelled():
                                timeout_handle.cancel()
                            if cancelled:
                                raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
                            return result
                        except asyncio.CancelledError:
                            if cancelled:
                                raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
                            raise
                    
                    return asyncio.run(run_with_timeout())
                else:
                    return asyncio.run(coroutine)
        except RuntimeError as e:
            # 如果 asyncio.run() 检测到运行中的循环，回退到手动实现
            if "cannot be called from a running event loop" not in str(e).lower() and "cannot run the event loop" not in str(e).lower():
                raise
        
        # 回退到手动实现：创建新的事件循环并运行
        loop = None
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            # 设置事件循环策略
            policy = asyncio.get_event_loop_policy()
            policy.set_event_loop(loop)
            
            # 如果指定了超时，手动实现超时逻辑
            if timeout:
                # 手动实现超时：创建一个任务和超时回调
                task = loop.create_task(coroutine)
                timeout_handle = None
                cancelled = False
                
                def cancel_task():
                    nonlocal cancelled
                    if not task.done():
                        cancelled = True
                        task.cancel()
                
                timeout_handle = loop.call_later(timeout, cancel_task)
                
                try:
                    # 使用 run_until_complete，但先确保没有运行中的循环
                    # 通过创建一个包装协程来避免直接检查
                    async def run_task():
                        return await task
                    
                    result = loop.run_until_complete(run_task())
                    
                    # 取消超时回调
                    if timeout_handle and not timeout_handle.cancelled():
                        timeout_handle.cancel()
                    if cancelled:
                        raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
                    return result
                except asyncio.CancelledError:
                    if cancelled:
                        raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
                    raise
            else:
                # 使用 run_until_complete，但先确保没有运行中的循环
                # 通过创建一个包装协程来避免直接检查
                async def run_coro():
                    return await coroutine
                return loop.run_until_complete(run_coro())
                
        finally:
            # 清理事件循环
            if loop:
                try:
                    # 取消所有待处理的任务
                    try:
                        pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                        if pending:
                            for task in pending:
                                task.cancel()
                            # 等待所有任务完成或取消
                            if pending:
                                async def gather_pending():
                                    await asyncio.gather(*pending, return_exceptions=True)
                                try:
                                    loop.run_until_complete(gather_pending())
                                except Exception:
                                    pass
                    except Exception:
                        pass
                except Exception:
                    pass
                try:
                    loop.close()
                except Exception:
                    pass
            # 清除事件循环引用
            try:
                policy = asyncio.get_event_loop_policy()
                policy.set_event_loop(None)
            except Exception:
                try:
                    asyncio.set_event_loop(None)
                except Exception:
                    pass
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread)
        total_timeout = (timeout + 5.0) if timeout else 30.0
        try:
            return future.result(timeout=total_timeout)
        except concurrent.futures.TimeoutError:
            raise asyncio.TimeoutError("Operation timed out")


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
        return get_media_url(url)

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


def get_media_duration(file_path):
    """
    使用 ffprobe 获取媒体文件的时长
    :param file_path: 文件路径
    :return: 时长（秒），如果失败返回 None
    """
    try:
        cmds = ['/usr/bin/ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
            'default=noprint_wrappers=1:nokey=1', file_path]
        result = subprocess.run(cmds, capture_output=True, text=True, timeout=50)
        if result.returncode == 0 and result.stdout.strip():
            duration = float(result.stdout.strip())
            return int(duration) if duration else None
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as e:
        log.warning(f"Failed to get media duration with ffprobe {' '.join(cmds)} error: {e}")
    except Exception as e:
        log.warning(f"Error getting media duration: {e}")
    return None


def _get_media_server_url():
    """获取媒体文件服务器的完整URL"""
    # 返回固定的服务器地址和端口
    return "http://mini:8848"


def decode_url_path(path: str) -> str:
    """
    解码 URL 编码的路径
    :param path: URL 编码的路径
    :return: 解码后的路径
    """
    while '%' in path:
        try:
            decoded = unquote(path)
            if decoded == path:
                break
            path = decoded
        except Exception:
            break
    return path


def validate_and_normalize_path(file_path: str, base_dir: str = '/mnt', must_be_file: bool = True) -> Tuple[Optional[str], Optional[str]]:
    """
    验证和规范化文件路径
    :param file_path: 文件路径
    :param base_dir: 基础目录，默认为 /mnt
    :param must_be_file: 是否必须是文件（True）或可以是目录（False）
    :return: (规范化后的路径, 错误消息)，如果成功则错误消息为 None
    """
    if not file_path:
        return None, "文件路径不能为空"
    
    # URL 解码
    file_path = decode_url_path(file_path)
    
    # 安全检查：防止路径遍历
    if '..' in file_path.split('/') or file_path.startswith('~'):
        return None, "Invalid path: Path traversal not allowed"
    
    # 处理相对路径
    if not os.path.isabs(file_path):
        file_path = os.path.join(base_dir, file_path.lstrip('/'))
        file_path = os.path.abspath(file_path)
    else:
        file_path = os.path.abspath(file_path)
    
    # 检查路径是否在允许的目录内
    if not file_path.startswith(base_dir):
        log.warning(f"Path {file_path} is outside allowed directory {base_dir}")
        return None, "文件路径不在允许的目录内"
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return None, "文件不存在"
    
    if must_be_file and not os.path.isfile(file_path):
        return None, "路径不是文件"
    
    return file_path, None


def get_media_url(local_path: str) -> str:
    """
    将本地文件路径转换为可通过 HTTP 访问的 URL
    :param local_path: 本地文件路径，如 /mnt/ext_base/audio/xxx.mp3
    :return: HTTP URL，如 http://192.168.1.100:8000/api/media/files/mnt/ext_base/audio/xxx.mp3
    """
    try:
        # 移除路径开头的 /
        if local_path.startswith('/'):
            filepath = local_path[1:]
        else:
            filepath = local_path
        
        # URL 编码路径
        encoded_path = '/'.join(quote(part, safe='') for part in filepath.split('/'))
        
        # 获取服务器URL（使用固定地址）
        base_url = _get_media_server_url()
        
        # 根据 main.py 中的 DispatcherMiddleware 配置，应用挂载在 /api 下
        # 所以完整路径是 /api/media/files/
        media_url = f"{base_url}/api/media/files/{encoded_path}"
        log.debug(f"[MEDIA] Converted {local_path} to {media_url}")
        return media_url
    except Exception as e:
        log.error(f"[MEDIA] Error converting path {local_path}: {e}")
        return local_path


def convert_standard_cron_weekday_to_apscheduler(day_of_week: str) -> str:
    """
    将标准 cron 的周几映射转换为 APScheduler 的周几映射
    
    标准 cron: 0=周日, 1=周一, 2=周二, 3=周三, 4=周四, 5=周五, 6=周六
    APScheduler: 0=周一, 1=周二, 2=周三, 3=周四, 4=周五, 5=周六, 6=周日
    
    转换公式: (标准cron + 6) % 7
    
    :param day_of_week: 标准 cron 的周几字段（可能是 *、数字、范围、列表等）
    :return: 转换后的 APScheduler 周几字段
    """
    if day_of_week == '*':
        return '*'

    def convert_single_day(day_str: str) -> str:
        """转换单个周几数字"""
        try:
            day_num = int(day_str)
            # 转换公式: (标准cron + 6) % 7
            apscheduler_day = (day_num + 6) % 7
            return str(apscheduler_day)
        except ValueError:
            # 如果不是数字，可能是字符串别名或其他格式，直接返回
            return day_str

    # 处理范围表达式，如 "1-5"
    if '-' in day_of_week:
        parts = day_of_week.split('-')
        if len(parts) == 2:
            start = convert_single_day(parts[0])
            end = convert_single_day(parts[1])
            return f"{start}-{end}"

    # 处理列表表达式，如 "1,3,5" 或 "*/2"
    if ',' in day_of_week:
        days = day_of_week.split(',')
        converted_days = [convert_single_day(day.strip()) for day in days]
        return ','.join(converted_days)

    # 处理步进表达式，如 "*/2" 或 "1-5/2"
    if '/' in day_of_week:
        parts = day_of_week.split('/')
        if len(parts) == 2:
            base = parts[0]
            step = parts[1]
            converted_base = convert_standard_cron_weekday_to_apscheduler(base)
            return f"{converted_base}/{step}"

    # 单个数字
    return convert_single_day(day_of_week)


def check_cron_will_trigger_today(cron_expression: str) -> bool:
    """
    检查 cron 表达式是否会在今天触发
    :param cron_expression: cron 表达式
    :return: True 如果今天会触发，False 否则
    """
    if not cron_expression or not cron_expression.strip():
        return False
    
    try:
        from apscheduler.triggers.cron import CronTrigger
        
        # 创建 CronTrigger
        parts = cron_expression.strip().split()
        if len(parts) == 6:
            second, minute, hour, day, month, day_of_week = parts
            converted_day_of_week = convert_standard_cron_weekday_to_apscheduler(day_of_week)
            trigger = CronTrigger(
                second=second,
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=converted_day_of_week
            )
        elif len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
            converted_day_of_week = convert_standard_cron_weekday_to_apscheduler(day_of_week)
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=converted_day_of_week
            )
        else:
            return False
        
        # 获取下一次执行时间
        now = datetime.now()
        next_run = trigger.get_next_fire_time(None, now)
        
        if next_run is None:
            return False
        
        # 处理时区问题：如果 next_run 是 timezone-aware，转换为 naive datetime
        if next_run.tzinfo is not None:
            # 转换为本地时区的 naive datetime
            next_run = next_run.astimezone().replace(tzinfo=None)
        
        # 判断下一次执行时间是否在今天
        today_start = datetime(now.year, now.month, now.day)
        today_end = today_start + timedelta(days=1)
        
        return today_start <= next_run < today_end
    except Exception as e:
        log.error(f"[Utils] 检查 cron 表达式失败: {cron_expression}, 错误: {e}")
        return False