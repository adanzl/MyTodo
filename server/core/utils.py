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
import tempfile
import shlex
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any, Union
from urllib.parse import quote, unquote
from flask import request
from queue import Queue, Empty
from werkzeug.utils import secure_filename

from core.config import app_logger

log = app_logger


def ok_response(data: Any = None) -> Dict[str, Any]:
    """返回成功响应。

    Args:
        data: 响应数据，可选。

    Returns:
        成功响应字典。
    """
    return {"code": 0, "msg": "ok", "data": data}


def err_response(message: str) -> Dict[str, Any]:
    """返回错误响应。

    Args:
        message: 错误消息。

    Returns:
        错误响应字典。
    """
    return {"code": -1, "msg": message}


# 为了保持向后兼容，提供别名
_ok = ok_response
_err = err_response


def get_json_body() -> Dict[str, Any]:
    """安全获取 JSON body（无 Content-Type 时返回空 dict，避免触发 415）。"""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def read_json_from_request() -> Dict[str, Any]:
    """从请求中读取 JSON 数据，使用 stream 方式避免 gevent 环境中的阻塞问题。

    Returns:
        解析后的 JSON 数据（dict），如果失败返回 {}。
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
    """将本地文件路径转换为 HTTP URL。

    Args:
        url: 本地文件路径（如 /opt/my_todo/data/ext_base/audio/xxx.mp3）或已经是 HTTP URL。

    Returns:
        HTTP URL。
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


def get_weekday_index() -> int:
    """获取当前星期对应的索引。

    Returns:
        int: 0=周一, 1=周二, 2=周三, 3=周四, 4=周五, 5=周六, 6=周日。
    """
    return datetime.now().weekday()


def format_time_str(seconds: float) -> str:
    """将秒数格式化为 "HH:MM:SS" 格式。

    Args:
        seconds: 秒数（可以是整数或浮点数）。

    Returns:
        "HH:MM:SS" 格式的时间字符串。
    """
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def time_to_seconds(time_str: str) -> int:
    """将 "HH:MM:SS" 格式的时间字符串转换为秒数。

    Args:
        time_str: "HH:MM:SS" 格式的时间字符串。

    Returns:
        秒数。
    """
    parts = time_str.split(':')
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]) if len(parts) == 3 else 0


def get_media_duration(file_path: str) -> Optional[int]:
    """使用 ffprobe 获取媒体文件的时长。

    在独立线程中使用 os.system 执行命令，避免 gevent 事件循环和 child watchers 问题。

    Args:
        file_path: 文件路径。

    Returns:
        时长（秒），如果失败返回 None。
    """
    import tempfile
    import shlex

    # 使用共享变量存储结果
    result_container = {'duration': None, 'error': None, 'command': None}

    def _run_ffprobe_in_thread():
        """在独立线程中运行 ffprobe"""
        try:
            # 创建临时文件存储输出
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as tmp_file:
                tmp_path = tmp_file.name

            try:
                # 构建命令，将 stdout 重定向到临时文件，stderr 重定向到 /dev/null 以过滤警告信息
                # 使用 -v quiet 进一步减少输出，只保留我们需要的时长信息
                cmd_str = f"/usr/bin/ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(file_path)} > {shlex.quote(tmp_path)} 2>/dev/null"
                result_container['command'] = cmd_str

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
                    with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        stdout = f.read().strip()
                except Exception:
                    stdout = ""

                # 如果输出有效，尝试解析时长（即使返回码非0）
                # 由于 stderr 已重定向到 /dev/null，输出应该只包含时长值
                if stdout:
                    try:
                        # 尝试解析整个输出（通常是单行浮点数）
                        duration = float(stdout)
                        result_container['duration'] = int(duration) if duration else None
                        # 如果成功解析，即使返回码非0也认为成功
                        return
                    except (ValueError, TypeError):
                        # 如果解析失败，尝试从多行输出中提取（容错处理）
                        lines = stdout.split('\n')
                        for line in reversed(lines):  # 从最后一行开始尝试
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                duration = float(line)
                                result_container['duration'] = int(duration) if duration else None
                                return
                            except (ValueError, TypeError):
                                continue

                        # 所有解析方法都失败
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
        cmd_info = f", command: {result_container['command']}" if result_container.get('command') else ""
        log.warning(f"[Utils] Error getting media duration for {file_path}: {result_container['error']}{cmd_info}")
        return None

    return result_container['duration']


def _get_media_server_url() -> str:
    """获取媒体文件服务器的完整 URL。"""
    # 返回固定的服务器地址和端口
    return "http://192.168.50.172:8848"


def decode_url_path(path: str) -> str:
    """解码 URL 编码的路径。

    Args:
        path: URL 编码的路径。

    Returns:
        解码后的路径。
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
                                base_dir: str = '/opt/my_todo/data',
                                must_be_file: bool = True) -> Tuple[Optional[str], Optional[str]]:
    """验证和规范化文件路径。

    Args:
        file_path: 文件路径。
        base_dir: 基础目录，默认为 /opt/my_todo/data。
        must_be_file: 是否必须是文件（True）或可以是目录（False）。

    Returns:
        (规范化后的路径, 错误消息)，如果成功则错误消息为 None。
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
    """将本地文件路径转换为可通过 HTTP 访问的 URL。

    Args:
        local_path: 本地文件路径，如 /opt/my_todo/data/ext_base/audio/xxx.mp3。

    Returns:
        HTTP URL，如 http://192.168.1.100:8000/api/media/files/opt/my_todo/data/ext_base/audio/xxx.mp3。
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
    """将标准 cron 的周几映射转换为 APScheduler 的周几映射。

    标准 cron: 0=周日, 1=周一, 2=周二, 3=周三, 4=周四, 5=周五, 6=周六
    APScheduler: 0=周一, 1=周二, 2=周三, 3=周四, 4=周五, 5=周六, 6=周日
    转换公式: (标准cron + 6) % 7

    Args:
        day_of_week: 标准 cron 的周几字段（可能是 *、数字、范围、列表等）。

    Returns:
        转换后的 APScheduler 周几字段。
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
    """检查 cron 表达式是否会在今天触发。

    Args:
        cron_expression: cron 表达式。

    Returns:
        True 如果今天会触发，False 否则。
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
    """确保目录存在，如果不存在则创建。

    Args:
        directory_path: 目录路径。
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
    except Exception as e:
        log.error(f"[Utils] 创建目录失败: {directory_path}, 错误: {e}")
        raise


def is_allowed_audio_file(filename: str) -> bool:
    """检查音频文件扩展名是否允许。

    Args:
        filename: 文件名。

    Returns:
        True 如果文件扩展名在允许列表中，False 否则。
    """
    from core.config import ALLOWED_AUDIO_EXTENSIONS
    return os.path.splitext(filename)[1].lower() in ALLOWED_AUDIO_EXTENSIONS


def is_allowed_pdf_file(filename: str) -> bool:
    """检查 PDF 文件扩展名是否允许。

    Args:
        filename: 文件名。

    Returns:
        True 如果文件扩展名在允许列表中，False 否则。
    """
    from core.config import ALLOWED_PDF_EXTENSIONS
    return os.path.splitext(filename)[1].lower() in ALLOWED_PDF_EXTENSIONS


def get_file_info(file_path: str) -> Optional[dict]:
    """获取文件信息。

    Args:
        file_path: 文件路径。

    Returns:
        包含文件信息的字典，如果文件不存在则返回 None。
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


def get_file_type_by_magic_number(file) -> Optional[str]:
    """通过文件头部的 magic number 来识别文件类型。

    Args:
        file: 文件对象 (werkzeug.FileStorage)。

    Returns:
        文件类型字符串（例如 'mp3', 'flac'），如果无法识别则返回 None。
    """
    magic_numbers = {
        b'\xFF\xFB': 'mp3',
        b'\xFF\xF3': 'mp3',
        b'\xFF\xF2': 'mp3',
        b'ID3': 'mp3',
        b'fLaC': 'flac',
        b'RIFF': 'wav',  # WAV and AVI
        b'OggS': 'ogg',
        b'\x00\x00\x00\x18ftypM4A': 'm4a',
        b'\x00\x00\x00\x14ftypmp42': 'mp4',
        b'\x00\x00\x00 ftyp': 'mp4',  # common for mp4 and mov
        b'\x30\x26\xb2\x75\x8e\x66\xcf\x11': 'wma',  # WMA/WMV
    }

    try:
        header = file.read(32)  # 读取文件头部的一些字节
        file.seek(0)  # 重置文件指针

        for magic, file_type in magic_numbers.items():
            if header.startswith(magic):
                # 特殊处理 WAV, 因为 RIFF 也用于 AVI
                if file_type == 'wav' and header[8:12] != b'WAVE':
                    continue
                return file_type
        return None
    except Exception as e:
        log.warning(f"[Utils] 检查 magic number 失败: {e}")
        return None


def get_unique_filepath(directory: str, base_name: str, extension: str) -> str:
    """生成唯一的文件路径，如果文件已存在则添加序号。

    Args:
        directory: 目标目录。
        base_name: 基础文件名（不含扩展名）。
        extension: 文件扩展名（包含点号，如 '.mp3'）。

    Returns:
        唯一的文件路径。
    """
    counter = 0
    while True:
        if counter == 0:
            filename = f"{base_name}{extension}"
        else:
            filename = f"{base_name}_{counter}{extension}"

        file_path = os.path.join(directory, filename)

        if not os.path.exists(file_path):
            return file_path

        counter += 1


def _cleanup_directory(directory: str, file_paths: Optional[List[str]] = None, is_temp: bool = False) -> None:
    """内部辅助函数：清理目录和文件。
    
    Args:
        directory: 目录路径
        file_paths: 文件路径列表（可选）
        is_temp: 是否为临时目录（临时目录会尝试删除空目录）
    """
    try:
        # 删除指定文件
        if file_paths:
            for path in file_paths:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
        
        # 如果是临时目录，尝试删除空目录
        if is_temp and directory and os.path.exists(directory):
            try:
                os.rmdir(directory)
            except Exception:
                pass
    except Exception:
        pass


def save_uploaded_files(
    files: List[Any],
    target_dir: Optional[str] = None,
    temp_prefix: str = 'upload_'
) -> Tuple[Optional[List[str]], Optional[str]]:
    """保存上传的文件到指定目录或临时目录。
    
    通用文件上传保存函数，支持两种模式：
    1. 保存到临时目录：target_dir=None，自动创建临时目录
    2. 保存到指定目录：target_dir 指定目标目录路径
    
    Args:
        files: Flask 文件对象列表（从 request.files.getlist() 获取）
        target_dir: 目标目录路径，None 表示使用临时目录
        temp_prefix: 临时目录前缀（仅在 target_dir=None 时使用）
    
    Returns:
        (file_paths, directory) 成功时返回文件路径列表和目录路径
        (None, None) 失败时返回 None
    
    Examples:
        # 保存到临时目录
        paths, temp_dir = save_uploaded_files(files, temp_prefix='ocr_')
        
        # 保存到指定目录
        paths, _ = save_uploaded_files(files, target_dir='/path/to/dir')
    """
    directory = None
    file_paths = []
    is_temp = target_dir is None
    
    try:
        # 确定目标目录
        if is_temp:
            directory = tempfile.mkdtemp(prefix=temp_prefix)
        else:
            directory = target_dir
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
        
        # 保存文件
        for file in files:
            if not file.filename:
                continue
            
            safe_filename = secure_filename(file.filename)
            file_path = os.path.join(directory, safe_filename)
            file.save(file_path)
            file_paths.append(file_path)
        
        # 检查是否有有效文件
        if not file_paths:
            _cleanup_directory(directory, is_temp=is_temp)
            return None, None
        
        return file_paths, directory
        
    except Exception as e:
        log.error(f"[Utils] 保存上传文件失败: {e}")
        _cleanup_directory(directory, file_paths, is_temp=is_temp)
        return None, None


def cleanup_temp_files(temp_dir: str, file_paths: Optional[List[str]] = None) -> None:
    """清理临时文件和目录。
    
    Args:
        temp_dir: 临时目录路径
        file_paths: 文件路径列表（可选，如果提供则只删除这些文件）
    """
    try:
        _cleanup_directory(temp_dir, file_paths, is_temp=True)
    except Exception as e:
        log.warning(f"[Utils] 清理临时文件失败: {e}")


def run_subprocess_safe(cmd: List[str],
                        timeout: float = 30.0,
                        env: Optional[Dict[str, str]] = None,
                        cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """在线程中安全地运行 subprocess，避免 gevent 与 asyncio 冲突。

    由于 gevent.monkey.patch_all(subprocess=True) 会 patch subprocess 模块，
    可能导致 "child watchers are only available on the default loop" 错误。
    直接使用 os.system + 临时文件的方案，完全避免 gevent 的 subprocess patch。

    Args:
        cmd: 要执行的命令列表。
        timeout: 超时时间（秒），默认 30 秒。
        env: 环境变量字典，可选。
        cwd: 工作目录，可选。

    Returns:
        (returncode, stdout, stderr) 元组。

    Raises:
        TimeoutError: 如果命令执行超时。
        FileNotFoundError: 如果命令未找到。
        Exception: 其他执行错误。
    """
    result_queue = queue.Queue()
    error_queue = queue.Queue()

    def _run():
        """在线程中使用 os.system + 临时文件运行命令，完全避免 gevent 的 subprocess patch"""
        try:
            _run_with_os_system(cmd, timeout, env, cwd, result_queue, error_queue)
        except Exception as e:
            error_queue.put(e)

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


def _run_with_os_system(cmd_list: List[str], timeout_val: float, env_dict: Optional[Dict[str, str]],
                        cwd_path: Optional[str], result_q: queue.Queue, error_q: queue.Queue) -> None:
    """使用 os.system + 临时文件的降级方案"""
    # 创建临时文件用于捕获输出
    stdout_path = None
    stderr_path = None
    returncode_path = None

    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.stdout') as tmp_stdout:
            stdout_path = tmp_stdout.name
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.stderr') as tmp_stderr:
            stderr_path = tmp_stderr.name
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.returncode') as tmp_rc:
            returncode_path = tmp_rc.name

        # 构建并执行命令
        shell_cmd = _build_shell_command(cmd_list, env_dict, cwd_path, stdout_path, stderr_path, returncode_path)
        returncode = _execute_with_timeout(shell_cmd, timeout_val, cmd_list, error_q)

        if returncode is None:  # 超时或出错
            return

        # 读取返回码和输出
        final_returncode = _read_returncode(returncode_path, returncode)
        stdout = _read_file_safe(stdout_path)
        stderr = _read_file_safe(stderr_path)

        result_q.put((final_returncode, stdout, stderr))

    except Exception as e:
        error_q.put(e)
    finally:
        # 清理临时文件
        _cleanup_temp_files([stdout_path, stderr_path, returncode_path])


def _build_shell_command(cmd_list: List[str], env_dict: Optional[Dict[str, str]], cwd_path: Optional[str],
                         stdout_path: str, stderr_path: str, returncode_path: str) -> str:
    """构建 shell 命令字符串"""
    quoted_cmd = ' '.join(shlex.quote(arg) for arg in cmd_list)

    if sys.platform == 'win32':
        return _build_windows_command(quoted_cmd, env_dict, cwd_path, stdout_path, stderr_path, returncode_path)
    else:
        return _build_unix_command(quoted_cmd, env_dict, cwd_path, stdout_path, stderr_path, returncode_path)


def _build_windows_command(quoted_cmd: str, env_dict: Optional[Dict[str, str]], cwd_path: Optional[str],
                           stdout_path: str, stderr_path: str, returncode_path: str) -> str:
    """构建 Windows 命令"""
    full_cmd_parts = []

    if cwd_path:
        full_cmd_parts.append(f'cd /d {shlex.quote(cwd_path)}')

    # 设置环境变量（Windows）
    if env_dict:
        for k, v in env_dict.items():
            # 使用引号包裹值，防止特殊字符问题
            full_cmd_parts.append(f'set {k}={shlex.quote(v)}')

    # 执行命令并重定向输出
    full_cmd_parts.append(f'{quoted_cmd} > {shlex.quote(stdout_path)} 2> {shlex.quote(stderr_path)}')

    # 捕获返回码
    full_cmd_parts.append(
        f'&& echo 0 > {shlex.quote(returncode_path)} || echo %ERRORLEVEL% > {shlex.quote(returncode_path)}')

    full_cmd = ' && '.join(full_cmd_parts)
    return f'cmd /c "{full_cmd}"'


def _build_unix_command(quoted_cmd: str, env_dict: Optional[Dict[str, str]], cwd_path: Optional[str], stdout_path: str,
                        stderr_path: str, returncode_path: str) -> str:
    """构建 Unix 命令"""
    # 构建环境变量部分
    env_cmd = ''
    if env_dict:
        env_parts = [f'{k}={shlex.quote(v)}' for k, v in env_dict.items()]
        env_cmd = 'env ' + ' '.join(env_parts) + ' '

    # 构建工作目录部分
    cd_cmd = f'cd {shlex.quote(cwd_path)} && ' if cwd_path else ''

    # 使用子shell确保返回码正确
    full_cmd = (f'{cd_cmd}({env_cmd}{quoted_cmd} > {shlex.quote(stdout_path)} '
                f'2> {shlex.quote(stderr_path)}); echo $? > {shlex.quote(returncode_path)}')

    return f'sh -c {shlex.quote(full_cmd)}'


def _execute_with_timeout(shell_cmd: str, timeout_val: float, cmd_list: List[str],
                          error_q: queue.Queue) -> Optional[int]:
    """使用线程执行命令并实现超时控制"""
    system_result = {'returncode': None, 'done': False, 'exception': None}

    def run_cmd():
        try:
            system_result['returncode'] = os.system(shell_cmd)
            system_result['done'] = True
        except Exception as e:
            system_result['exception'] = e
            system_result['done'] = True

    cmd_thread = threading.Thread(target=run_cmd, daemon=True)
    cmd_thread.start()
    cmd_thread.join(timeout=timeout_val)

    if system_result['exception']:
        error_q.put(system_result['exception'])
        return None

    if not system_result['done']:
        error_q.put(TimeoutError(f"命令执行超时: {' '.join(cmd_list)}"))
        return None

    return system_result['returncode']


def _read_returncode(returncode_path: Optional[str], system_returncode: Optional[int]) -> int:
    """读取返回码，优先从文件读取"""
    if returncode_path:
        try:
            with open(returncode_path, 'r', encoding='utf-8') as f:
                returncode_str = f.read().strip()
                if returncode_str.isdigit():
                    return int(returncode_str)
        except Exception:
            pass

    # 降级：使用 os.system 的返回值
    if system_returncode is not None:
        if sys.platform == 'win32':
            return system_returncode
        else:
            return system_returncode >> 8 if system_returncode else 0

    return 0


def _read_file_safe(file_path: Optional[str]) -> str:
    """安全地读取文件内容"""
    if not file_path:
        return ''

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception:
        return ''


def _cleanup_temp_files(file_paths: List[Optional[str]]) -> None:
    """清理临时文件"""
    for file_path in file_paths:
        if file_path:
            try:
                os.unlink(file_path)
            except Exception:
                pass
