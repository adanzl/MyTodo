'''
工具函数
'''
import asyncio
import os
import shutil
import socket
from typing import Optional
import requests
from flask import jsonify
from core.log_config import root_logger
# 使用 gevent.subprocess（通过 monkey.patch_all 自动替换）
from gevent import spawn, subprocess

log = root_logger()


def _ok(data=None, msg="ok"):
    """
    返回成功响应
    :param data: 响应数据
    :param msg: 响应消息
    :return: JSON响应
    """
    return jsonify({"code": 0, "msg": msg, "data": data})


def _err(msg="error", code=-1):
    """
    返回错误响应
    :param msg: 错误消息
    :param code: 错误代码，默认为-1
    :return: JSON响应
    """
    return jsonify({"code": code, "msg": msg})


def _convert_result(result):
    """
    将字典格式的结果转换为统一的响应格式
    :param result: 字典格式的结果或已经是响应对象
    :return: JSON响应
    """
    # 如果已经是响应对象，直接返回
    if hasattr(result, 'status_code'):
        return result
    
    # 如果是字典格式，转换为响应
    if isinstance(result, dict):
        code = result.get('code', -1)
        msg = result.get('msg', 'error' if code != 0 else 'ok')
        data = result.get('data')
        
        if code == 0:
            return _ok(data=data, msg=msg)
        else:
            return _err(msg=msg, code=code)
    
    # 其他情况直接返回
    return result


def _handle_service_result(success: bool, message: str, data=None):
    """
    统一处理服务返回结果
    :param success: 是否成功
    :param message: 消息
    :param data: 数据
    :return: Flask 响应
    """
    if success:
        return _ok(data=data, msg=message)
    return _err(msg=message)


def _send_http_request(url: str, method: str = 'GET', data: dict = None, headers: dict = None):
    """
    发送 HTTP 请求
    :param url: 请求 URL
    :param method: HTTP 方法 (GET, POST, PUT, DELETE)
    :param data: 请求数据（用于 POST/PUT）
    :param headers: 请求头
    :return: 响应结果
    """
    try:
        method = method.upper()
        timeout = 5  # 5秒超时
        
        # 使用字典映射简化方法调用
        method_map = {
            'GET': requests.get,
            'POST': requests.post,
            'PUT': requests.put,
            'DELETE': requests.delete
        }
        
        request_func = method_map.get(method)
        if not request_func:
            return {"success": False, "error": f"不支持的 HTTP 方法: {method}"}
        
        # 统一处理请求参数
        kwargs = {'headers': headers, 'timeout': timeout}
        if method in ('POST', 'PUT') and data:
            kwargs['json'] = data
        
        response = request_func(url, **kwargs)
        
        return {
            "success": True,
            "status_code": response.status_code,
            "response": response.text[:500]  # 限制响应长度
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "请求超时"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"未知错误: {str(e)}"}


def get_local_ip() -> str:
    """
    获取本机IP地址
    :return: IP地址字符串
    """
    try:
        # 连接到一个远程地址来获取本机IP（不实际发送数据）
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.connect(('8.8.8.8', 80))
                return s.getsockname()[0]
            except Exception:
                return '127.0.0.1'
    except Exception:
        return '127.0.0.1'


def find_command(cmd_name: str) -> Optional[str]:
    """
    查找命令的完整路径
    :param cmd_name: 命令名称
    :return: 命令的完整路径，如果未找到则返回 None
    """
    # 首先尝试使用 shutil.which
    cmd_path = shutil.which(cmd_name)
    if cmd_path:
        return cmd_path

    # 如果找不到，尝试常见路径
    common_paths = [
        "/usr/bin",
        "/usr/local/bin",
        "/bin",
        "/sbin",
        "/usr/sbin",
    ]
    for path in common_paths:
        full_path = os.path.join(path, cmd_name)
        if os.path.exists(full_path) and os.access(full_path, os.X_OK):
            return full_path

    return None


def run_async(coro, timeout: float = None, log_prefix: str = ""):
    """
    在新的事件循环中运行协程
    :param coro: 协程对象
    :param timeout: 超时时间（秒），如果为 None 则不设置超时
    :param log_prefix: 日志前缀，用于标识调用来源
    :return: 协程的返回值
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if timeout:
            return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
        else:
            return loop.run_until_complete(coro)
    except asyncio.TimeoutError:
        prefix = f"[{log_prefix}] " if log_prefix else ""
        log.error(f"{prefix}Async operation timeout after {timeout}s")
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


def run_subprocess_safe(cmd, timeout=10, env=None, log_prefix=""):
    """
    在 gevent 环境中安全地运行 subprocess
    :param cmd: 要执行的命令（列表或字符串）
    :param timeout: 超时时间（秒）
    :param env: 环境变量字典
    :param log_prefix: 日志前缀，用于标识调用来源
    :return: (returncode, stdout, stderr) 元组
    """
    def _run():
        try:
            # 如果是字符串命令，尝试查找完整路径
            if isinstance(cmd, list) and len(cmd) > 0:
                cmd_name = cmd[0]
                cmd_path = find_command(cmd_name)
                if cmd_path:
                    cmd[0] = cmd_path

            # 设置环境变量，确保包含系统 PATH
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
            # 确保 PATH 包含常见路径
            if 'PATH' not in process_env or not process_env['PATH']:
                process_env['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
            else:
                # 确保常见路径在 PATH 中
                common_paths = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
                if common_paths not in process_env['PATH']:
                    process_env['PATH'] = f"{process_env['PATH']}:{common_paths}"

            process = subprocess.Popen(cmd,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       text=True,
                                       env=process_env)
            stdout, stderr = process.communicate(timeout=timeout)
            return process.returncode, stdout, stderr
        except FileNotFoundError as e:
            # 命令不存在
            prefix = f"[{log_prefix}] " if log_prefix else ""
            log.warning(f"{prefix}Command not found: {cmd[0] if isinstance(cmd, list) else cmd}")
            return -2, "", str(e)
        except Exception as e:
            prefix = f"[{log_prefix}] " if log_prefix else ""
            log.error(f"{prefix}Subprocess error: {e}")
            return -1, "", str(e)

    # 在独立的 greenlet 中运行，避免阻塞 gevent 事件循环
    greenlet = spawn(_run)
    return greenlet.get(timeout=timeout + 2)
