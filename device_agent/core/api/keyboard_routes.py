'''
键盘监听路由
'''
from functools import wraps
from typing import Dict, Tuple, Optional, Any, Callable
from flask import Blueprint, request
from core.log_config import root_logger
from core.utils import _ok, _err, _handle_service_result
from core.service.keyboard_mgr import KEY_CODES, keyboard_mgr

log = root_logger()
keyboard_bp = Blueprint('keyboard', __name__)

# HTTP 方法白名单
ALLOWED_METHODS = {'GET', 'POST', 'PUT', 'DELETE'}


def handle_errors(operation_name: str):
    """
    错误处理装饰器，统一处理路由函数的异常
    :param operation_name: 操作名称，用于日志记录
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log.error(f"[KEYBOARD] {operation_name}失败: {e}", exc_info=True)
                return _err(msg=f'{operation_name}失败: {str(e)}')
        return wrapper
    return decorator


def _validate_key(key: Optional[str]) -> Tuple[bool, str]:
    """
    验证按键参数
    :param key: 按键名
    :return: (is_valid: bool, error_message: str)
    """
    if not key:
        return False, "key 参数是必需的"
    if key not in KEY_CODES:
        return False, f"不支持的按键: {key}，仅支持 {', '.join(KEY_CODES.keys())}"
    return True, ""


def _validate_config_params(args: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    验证配置参数
    :param args: 请求参数
    :return: (is_valid: bool, error_message: str, params: dict)
    """
    key = args.get('key')
    is_valid, error = _validate_key(key)
    if not is_valid:
        return False, error, {}

    url = args.get('url')
    if not url:
        return False, "url 参数是必需的", {}

    method = args.get('method', 'GET').upper()
    if method not in ALLOWED_METHODS:
        return False, f"不支持的 HTTP 方法: {method}，仅支持 {', '.join(ALLOWED_METHODS)}", {}

    return True, "", {
        "key": key,
        "url": url,
        "method": method,
        "data": args.get('data')
    }


@keyboard_bp.route("/keyboard/status", methods=['GET'])
@handle_errors("获取键盘状态")
def keyboard_status():
    """
    获取键盘监听服务状态
    GET /keyboard/status
    """
    log.info("===== [Keyboard Status] =====")
    status = keyboard_mgr.get_keyboard_status()
    return _ok(data=status)


@keyboard_bp.route("/keyboard/start", methods=['POST'])
@handle_errors("启动键盘服务")
def keyboard_start():
    """
    启动键盘监听服务
    POST /keyboard/start
    """
    success, message = keyboard_mgr.start_service()
    return _handle_service_result(success, message)


@keyboard_bp.route("/keyboard/stop", methods=['POST'])
@handle_errors("停止键盘服务")
def keyboard_stop():
    """
    停止键盘监听服务
    POST /keyboard/stop
    """
    success, message = keyboard_mgr.stop_service()
    return _handle_service_result(success, message)


@keyboard_bp.route("/keyboard/config", methods=['GET'])
@handle_errors("获取按键配置")
def keyboard_get_config():
    """
    获取按键配置
    GET /keyboard/config?key=F13  # 获取单个按键配置
    GET /keyboard/config           # 获取所有按键配置
    """
    key = request.args.get('key')
    config = keyboard_mgr.get_key_config(key)

    if key and not config:
        return _err(msg=f"按键 {key} 未配置")

    return _ok(data=config, msg="获取配置成功")


@keyboard_bp.route("/keyboard/config/set", methods=['POST'])
@handle_errors("设置按键配置")
def keyboard_set_config():
    """
    设置或删除按键配置
    POST /keyboard/config/set
    
    设置配置:
    {
        "key": "F13",
        "url": "http://example.com/api",
        "method": "POST",
        "data": {"action": "test"}
    }
    
    删除配置:
    {
        "key": "F13",
        "delete": 1
    }
    """
    args = request.get_json() or {}
    key = args.get('key')

    # 验证 key 参数
    is_valid, error = _validate_key(key)
    if not is_valid:
        return _err(msg=error)

    # 检查是否是删除操作
    if args.get('delete') == 1:
        success, message = keyboard_mgr.delete_key_config(key)
        return _handle_service_result(success, message)

    # 设置配置
    is_valid, error, params = _validate_config_params(args)
    if not is_valid:
        return _err(msg=error)

    success, message, config_data = keyboard_mgr.save_key_config(
        params["key"], params["url"], params["method"], params["data"]
    )
    return _handle_service_result(success, message, config_data)


@keyboard_bp.route("/keyboard/mock", methods=['POST'])
@handle_errors("模拟按键触发")
def keyboard_mock():
    """
    模拟按键触发
    POST /keyboard/mock
    {
        "key": "F13"
    }
    """
    args = request.get_json() or {}
    log.info(f"===== [Keyboard Mock] {args}")
    key = args.get('key')

    is_valid, error = _validate_key(key)
    if not is_valid:
        return _err(msg=error)

    success, message, result = keyboard_mgr.simulate_key_press(key)
    return _handle_service_result(success, message, result)
