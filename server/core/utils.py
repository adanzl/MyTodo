"""
通用工具函数
包含异步工具函数和其他通用工具函数
"""
import os
import subprocess
import json
import sys
import threading
import queue
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import quote, unquote
from flask import request
from queue import Queue, Empty

from core.log_config import app_logger

log = app_logger


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


def read_json_from_request():
    """
    从请求中读取 JSON 数据，使用 stream 方式避免 gevent 环境中的阻塞问题
    :return: 解析后的 JSON 数据（dict），如果失败返回 {}
    """
    try:
        content_length = request.content_length or 0
        if content_length > 0:
            raw_data = request.stream.read(content_length)
        else:
            raw_data = request.stream.read()

        if raw_data:
            return json.loads(raw_data.decode('utf-8'))
        return {}
    except Exception as e:
        log.warning(f"[read_json_from_request] 读取 JSON 失败，降级到 request.get_json(): {e}")
        try:
            return request.get_json(silent=True) or {}
        except Exception:
            return {}


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
    在独立线程中使用 os.system 执行命令，避免 gevent 事件循环和 child watchers 问题
    :param file_path: 文件路径
    :return: 时长（秒），如果失败返回 None
    """
    import tempfile
    import shlex

    # 使用共享变量存储结果
    result_container = {'duration': None, 'error': None}

    def _run_ffprobe_in_thread():
        """在独立线程中运行 ffprobe"""
        try:
            # 创建临时文件存储输出
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as tmp_file:
                tmp_path = tmp_file.name

            try:
                # 构建命令，将输出重定向到临时文件
                cmd_str = f"/usr/bin/ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(file_path)} > {shlex.quote(tmp_path)} 2>&1"

                # 使用 os.system 执行命令（返回退出码）
                returncode = os.system(cmd_str)
                # os.system 返回值的处理：
                # - 正常情况：返回 (退出码 << 8)，需要右移8位获取退出码
                # - 异常情况：可能返回 -1（进程被信号中断等）
                if returncode == -1:
                    # 返回 -1 可能是进程被信号中断，但命令可能已经成功执行
                    # 尝试读取输出，如果输出有效则忽略返回码
                    returncode = 0  # 假设成功，后续通过输出判断
                else:
                    returncode = returncode >> 8 if returncode else 0  # 提取退出码

                # 读取输出（即使返回码非0也尝试读取，因为某些情况下命令可能成功但返回非0）
                try:
                    with open(tmp_path, 'r') as f:
                        stdout = f.read().strip()
                except Exception:
                    stdout = ""

                # 如果输出有效，尝试解析时长（即使返回码非0）
                if stdout:
                    try:
                        duration = float(stdout)
                        result_container['duration'] = int(duration) if duration else None
                        # 如果成功解析，即使返回码非0也认为成功
                        return
                    except (ValueError, TypeError):
                        result_container['error'] = f"Invalid duration value: {stdout}"
                else:
                    # 没有输出且返回码非0，认为失败
                    result_container['error'] = f"ffprobe failed: returncode={returncode}, no output"

            finally:
                # 清理临时文件
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except FileNotFoundError as e:
            result_container['error'] = f"ffprobe not found: {e}"
        except Exception as e:
            result_container['error'] = str(e)

    # 在独立线程中运行
    thread = threading.Thread(target=_run_ffprobe_in_thread, daemon=True)
    thread.start()
    thread.join(timeout=55)  # 等待线程完成

    if thread.is_alive():
        log.warning(f"[Utils] ffprobe thread timeout for {file_path}")
        return None

    # 检查结果
    if result_container['error']:
        log.warning(f"[Utils] Error getting media duration for {file_path}: {result_container['error']}")
        return None

    return result_container['duration']


def _get_media_server_url():
    """获取媒体文件服务器的完整URL"""
    # 返回固定的服务器地址和端口
    return "http://192.168.50.172:8848"


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


def validate_and_normalize_path(file_path: str,
                                base_dir: str = '/mnt',
                                must_be_file: bool = True) -> Tuple[Optional[str], Optional[str]]:
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
            trigger = CronTrigger(second=second,
                                  minute=minute,
                                  hour=hour,
                                  day=day,
                                  month=month,
                                  day_of_week=converted_day_of_week)
        elif len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
            converted_day_of_week = convert_standard_cron_weekday_to_apscheduler(day_of_week)
            trigger = CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=converted_day_of_week)
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


def ensure_directory(directory_path: str) -> None:
    """
    确保目录存在，如果不存在则创建
    :param directory_path: 目录路径
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
    except Exception as e:
        log.error(f"[Utils] 创建目录失败: {directory_path}, 错误: {e}")
        raise


def is_allowed_audio_file(filename: str) -> bool:
    """
    检查音频文件扩展名是否允许
    :param filename: 文件名
    :return: True 如果文件扩展名在允许列表中，False 否则
    """
    from core.models.const import ALLOWED_AUDIO_EXTENSIONS
    return os.path.splitext(filename)[1].lower() in ALLOWED_AUDIO_EXTENSIONS


def is_allowed_pdf_file(filename: str) -> bool:
    """
    检查 PDF 文件扩展名是否允许
    :param filename: 文件名
    :return: True 如果文件扩展名在允许列表中，False 否则
    """
    from core.models.const import ALLOWED_PDF_EXTENSIONS
    return os.path.splitext(filename)[1].lower() in ALLOWED_PDF_EXTENSIONS


def is_allowed_file(filename: str, allowed_extensions: set) -> bool:
    """
    检查文件扩展名是否在允许的扩展名集合中
    :param filename: 文件名
    :param allowed_extensions: 允许的扩展名集合
    :return: True 如果文件扩展名在允许列表中，False 否则
    """
    return os.path.splitext(filename)[1].lower() in allowed_extensions


def get_file_info(file_path: str) -> Optional[dict]:
    """
    获取文件信息
    :param file_path: 文件路径
    :return: 包含文件信息的字典，如果文件不存在则返回 None
    """
    if not os.path.exists(file_path):
        return None

    stat_info = os.stat(file_path)
    return {
        "name": os.path.basename(file_path),
        "path": file_path,
        "size": stat_info.st_size,
        "modified": stat_info.st_mtime,
    }


def get_unique_filepath(directory: str, base_name: str, extension: str) -> str:
    """
    生成唯一的文件路径，如果文件已存在则添加序号
    
    :param directory: 目标目录
    :param base_name: 基础文件名（不含扩展名）
    :param extension: 文件扩展名（包含点号，如 '.mp3'）
    :return: 唯一的文件路径
    """
    filename = f"{base_name}{extension}"
    file_path = os.path.join(directory, filename)

    if os.path.exists(file_path):
        counter = 1
        while os.path.exists(file_path):
            filename = f"{base_name}_{counter}{extension}"
            file_path = os.path.join(directory, filename)
            counter += 1

    return file_path


def run_subprocess_safe(
    cmd: List[str],
    timeout: float = 30.0,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None
) -> Tuple[int, str, str]:
    """
    在线程中安全地运行 subprocess，避免 gevent 与 asyncio 冲突
    
    由于 gevent.monkey.patch_all(subprocess=True) 会 patch subprocess 模块，
    可能导致 "child watchers are only available on the default loop" 错误。
    使用 threading.Thread + subprocess.Popen 但设置进程隔离参数来避免 gevent 的影响。
    
    :param cmd: 要执行的命令列表
    :param timeout: 超时时间（秒），默认 30 秒
    :param env: 环境变量字典，可选
    :param cwd: 工作目录，可选
    :return: (returncode, stdout, stderr) 元组
    :raises TimeoutError: 如果命令执行超时
    :raises FileNotFoundError: 如果命令未找到
    :raises Exception: 其他执行错误
    """
    result_queue = queue.Queue()
    error_queue = queue.Queue()
    
    def _run():
        """在线程中运行 subprocess，通过设置进程隔离参数避免 gevent 冲突"""
        try:
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
            
            # 尝试使用 subprocess.Popen，但捕获 gevent 相关的错误
            try:
                # 准备 subprocess.Popen 的参数
                popen_kwargs = {
                    'args': cmd,
                    'stdout': subprocess.PIPE,
                    'stderr': subprocess.PIPE,
                    'text': True,
                    'env': process_env if env else None,
                    'cwd': cwd,
                    'close_fds': True,  # 关闭所有文件描述符（除了标准输入/输出/错误）
                }
                
                # 在 Unix 系统上，设置 start_new_session 来创建新的进程组
                # 这样可以完全隔离进程，避免 gevent 的监控
                if sys.platform != 'win32':
                    popen_kwargs['start_new_session'] = True
                
                # 在 Windows 上，使用 CREATE_NEW_PROCESS_GROUP 标志
                if sys.platform == 'win32':
                    import subprocess as sp
                    popen_kwargs['creationflags'] = sp.CREATE_NEW_PROCESS_GROUP
                
                # 创建进程
                process = subprocess.Popen(**popen_kwargs)
                
                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                    result_queue.put((process.returncode, stdout, stderr))
                except subprocess.TimeoutExpired:
                    # 超时：终止进程
                    try:
                        if sys.platform == 'win32':
                            # Windows: 使用 taskkill 强制终止进程树
                            import subprocess as sp
                            sp.Popen(['taskkill', '/F', '/T', '/PID', str(process.pid)],
                                    stdout=sp.DEVNULL, stderr=sp.DEVNULL)
                        else:
                            # Unix: 终止进程组
                            os.killpg(os.getpgid(process.pid), 9)
                    except Exception:
                        # 如果终止失败，尝试普通 kill
                        try:
                            process.kill()
                        except Exception:
                            pass
                    try:
                        process.wait(timeout=1)
                    except Exception:
                        pass
                    error_queue.put(TimeoutError(f"命令执行超时: {' '.join(cmd)}"))
            except (RuntimeError, AttributeError) as e:
                # 捕获 gevent 相关的错误："child watchers are only available on the default loop"
                # 如果出现这个错误，使用 os.system + 临时文件作为降级方案
                if 'child watchers' in str(e) or 'default loop' in str(e):
                    log.warning(f"[run_subprocess_safe] 检测到 gevent 冲突，使用降级方案: {e}")
                    _run_with_os_system(cmd, timeout, env, cwd, result_queue, error_queue)
                else:
                    raise
        except FileNotFoundError as e:
            error_queue.put(FileNotFoundError(f"命令未找到: {cmd[0] if cmd else 'unknown'}"))
        except Exception as e:
            error_queue.put(e)
    
    def _run_with_os_system(cmd_list, timeout_val, env_dict, cwd_path, result_q, error_q):
        """使用 os.system + 临时文件的降级方案"""
        import tempfile
        import shlex
        import time
        
        try:
            # 创建临时文件用于捕获输出
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.stdout') as tmp_stdout:
                stdout_path = tmp_stdout.name
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.stderr') as tmp_stderr:
                stderr_path = tmp_stderr.name
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.returncode') as tmp_rc:
                returncode_path = tmp_rc.name
            
            try:
                # 构建命令字符串
                quoted_cmd = ' '.join(shlex.quote(arg) for arg in cmd_list)
                
                # 设置环境变量
                env_str = ''
                if env_dict:
                    if sys.platform == 'win32':
                        env_parts = [f'{k}={v}' for k, v in env_dict.items()]
                        env_str = ' '.join(env_parts) + ' '
                    else:
                        env_parts = [f'{k}={shlex.quote(v)}' for k, v in env_dict.items()]
                        env_str = ' '.join(env_parts) + ' '
                
                # 构建完整的命令
                if sys.platform == 'win32':
                    full_cmd = f'cd /d {shlex.quote(cwd_path)} && ' if cwd_path else ''
                    full_cmd += f'{env_str}{quoted_cmd} > {shlex.quote(stdout_path)} 2> {shlex.quote(stderr_path)} && echo 0 > {shlex.quote(returncode_path)} || echo %ERRORLEVEL% > {shlex.quote(returncode_path)}'
                    shell_cmd = f'cmd /c "{full_cmd}"'
                else:
                    cd_cmd = f'cd {shlex.quote(cwd_path)} && ' if cwd_path else ''
                    full_cmd = f'{cd_cmd}{env_str}{quoted_cmd} > {shlex.quote(stdout_path)} 2> {shlex.quote(stderr_path)}; echo $? > {shlex.quote(returncode_path)}'
                    shell_cmd = f'sh -c {shlex.quote(full_cmd)}'
                
                # 使用 threading 和 os.system 来实现超时
                import threading as th
                system_result = {'returncode': None, 'done': False}
                
                def run_cmd():
                    system_result['returncode'] = os.system(shell_cmd)
                    system_result['done'] = True
                
                cmd_thread = th.Thread(target=run_cmd, daemon=True)
                cmd_thread.start()
                cmd_thread.join(timeout=timeout_val)
                
                if not system_result['done']:
                    error_q.put(TimeoutError(f"命令执行超时: {' '.join(cmd_list)}"))
                    return
                
                # 读取返回码
                try:
                    with open(returncode_path, 'r') as f:
                        returncode_str = f.read().strip()
                        returncode = int(returncode_str) if returncode_str.isdigit() else (system_result['returncode'] >> 8 if system_result['returncode'] else 0)
                except Exception:
                    returncode = system_result['returncode'] >> 8 if system_result['returncode'] else 0
                
                # 读取输出
                try:
                    with open(stdout_path, 'r', encoding='utf-8', errors='replace') as f:
                        stdout = f.read()
                except Exception:
                    stdout = ''
                
                try:
                    with open(stderr_path, 'r', encoding='utf-8', errors='replace') as f:
                        stderr = f.read()
                except Exception:
                    stderr = ''
                
                result_q.put((returncode, stdout, stderr))
                
            finally:
                # 清理临时文件
                for tmp_file in [stdout_path, stderr_path, returncode_path]:
                    try:
                        os.unlink(tmp_file)
                    except Exception:
                        pass
        except Exception as e:
            error_q.put(e)
    
    # 在独立线程中运行
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout + 5)  # 给一些额外时间
    
    # 检查线程是否还在运行（超时）
    if thread.is_alive():
        error_queue.put(TimeoutError(f"命令执行超时: {' '.join(cmd)}"))
    
    # 检查是否有错误
    if not error_queue.empty():
        error = error_queue.get()
        raise error
    
    # 检查是否有结果
    if result_queue.empty():
        raise TimeoutError(f"命令执行超时或进程异常退出: {' '.join(cmd)}")
    
    return result_queue.get()
