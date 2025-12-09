'''
键盘监听路由
'''
from flask import Blueprint, request
from core.log_config import root_logger
from core.utils import _ok, _err
from core.service.keyboard import (
    KEY_CODES,
    get_keyboard_status,
    start_keyboard_service,
    stop_keyboard_service,
    get_key_config,
    save_key_config,
    delete_key_config,
    simulate_key_press,
)

log = root_logger()
keyboard_bp = Blueprint('keyboard', __name__)

# HTTP 方法白名单
ALLOWED_METHODS = {'GET', 'POST', 'PUT', 'DELETE'}


def _validate_key(key: str) -> tuple[bool, str]:
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


def _validate_config_params(args: dict) -> tuple[bool, str, dict]:
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
def keyboard_status():
    """
    获取键盘监听服务状态
    """
    try:
        log.info(f"===== [Keyboard Status] =====")
        status = get_keyboard_status()
        return _ok(data=status)
    except Exception as e:
        log.error(f"[KEYBOARD] 获取状态失败: {e}")
        return _err(msg=f'error: {str(e)}')


@keyboard_bp.route("/keyboard/start", methods=['POST'])
def keyboard_start():
    """
    启动键盘监听服务
    """
    try:
        success, message = start_keyboard_service()
        if success:
            return _ok(msg=message)
        else:
            return _err(msg=message)
    except Exception as e:
        log.error(f"[KEYBOARD] 启动服务失败: {e}")
        return _err(msg=f'error: {str(e)}')


@keyboard_bp.route("/keyboard/stop", methods=['POST'])
def keyboard_stop():
    """
    停止键盘监听服务
    """
    try:
        success, message = stop_keyboard_service()
        if success:
            return _ok(msg=message)
        else:
            return _err(msg=message)
    except Exception as e:
        log.error(f"[KEYBOARD] 停止服务失败: {e}")
        return _err(msg=f'error: {str(e)}')


@keyboard_bp.route("/keyboard/config", methods=['GET'])
def keyboard_get_config():
    """
    获取按键配置
    GET /keyboard/config?key=F13  # 获取单个按键配置
    GET /keyboard/config           # 获取所有按键配置
    """
    try:
        key = request.args.get('key')
        config = get_key_config(key)

        if key and not config:
            return _err(msg=f"按键 {key} 未配置")

        return _ok(data=config, msg="获取配置成功")
    except Exception as e:
        log.error(f"[KEYBOARD] 获取配置失败: {e}")
        return _err(msg=f'error: {str(e)}')



@keyboard_bp.route("/keyboard/config/set", methods=['POST'])
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
    try:
        args = request.get_json() or {}
        key = args.get('key')

        # 验证 key 参数
        is_valid, error = _validate_key(key)
        if not is_valid:
            return _err(msg=error)

        # 检查是否是删除操作
        delete = args.get('delete')
        if delete == 1:
            success, message = delete_key_config(key)
            if success:
                return _ok(msg=message)
            else:
                return _err(msg=message)

        # 设置配置
        is_valid, error, params = _validate_config_params(args)
        if not is_valid:
            return _err(msg=error)

        success, message, config_data = save_key_config(
            params["key"], params["url"], params["method"], params["data"]
        )
        if success:
            return _ok(data=config_data, msg=message)
        else:
            return _err(msg=message)

    except Exception as e:
        log.error(f"[KEYBOARD] 设置配置失败: {e}")
        return _err(msg=f'error: {str(e)}')


@keyboard_bp.route("/keyboard/test", methods=['POST'])
def keyboard_test():
    """
    模拟按键触发
    POST /keyboard/test
    {
        "key": "F13"
    }
    """
    try:
        args = request.get_json() or {}
        key = args.get('key')

        is_valid, error = _validate_key(key)
        if not is_valid:
            return _err(msg=error)

        success, message, result = simulate_key_press(key)
        if success:
            return _ok(data=result, msg=message)
        else:
            return _err(msg=message)

    except Exception as e:
        log.error(f"[KEYBOARD] 模拟按键失败: {e}")
        return _err(msg=f'error: {str(e)}')
