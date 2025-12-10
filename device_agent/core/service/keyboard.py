'''
键盘监听服务
监听 F12~F19 按键并发送 HTTP 请求
'''
import json
import platform
import threading
import time
import traceback
from typing import Dict, Optional, Callable
from core.log_config import root_logger
from core.config import config_mgr
from core.utils import _send_http_request

from pynput import keyboard

log = root_logger()

# F12~F19 的按键映射（pynput 使用 keyboard.Key.f12 等）
KEY_CODES = {f'F{i}': getattr(keyboard.Key, f'f{i}', None) for i in range(12, 20)}
# 过滤掉 None 值（如果某个键不存在）
KEY_CODES = {k: v for k, v in KEY_CODES.items() if v is not None}

# 反转映射：按键对象 -> 按键名
KEY_TO_NAME = {v: k for k, v in KEY_CODES.items() if v is not None}


class KeyboardListener:
    """键盘监听器"""

    def __init__(self):
        self.is_running = False
        self.listener_thread: Optional[threading.Thread] = None
        self.listener: Optional[object] = None  # keyboard.Listener 类型
        self.handlers: Dict[str, Callable] = {}  # 按键名 -> 处理函数
        self._lock = threading.Lock()

    def set_handler(self, key: str, handler: Callable):
        """
        设置按键处理函数
        :param key: 按键名 (F12~F19)
        :param handler: 处理函数，接收按键名作为参数
        """
        if key not in KEY_CODES:
            raise ValueError(f"不支持的按键: {key}，仅支持 F12~F19")

        with self._lock:
            self.handlers[key] = handler

    def remove_handler(self, key: str):
        """移除按键处理函数"""
        with self._lock:
            if key in self.handlers:
                del self.handlers[key]
                log.info(f"[KEYBOARD] 移除 {key} 的处理函数")

    def clear_handlers(self):
        """清除所有处理函数"""
        with self._lock:
            self.handlers.clear()
            log.info("[KEYBOARD] 清除所有处理函数")

    def _on_key_press(self, key):
        """按键按下事件处理"""
        if not self.is_running:
            return False

        # 检查是否是 F12~F19
        if key in KEY_TO_NAME:
            key_name = KEY_TO_NAME[key]
            # log.info(f"[KEYBOARD] 检测到按键: {key_name}")

            # 调用对应的处理函数
            with self._lock:
                handler = self.handlers.get(key_name)

            if handler:
                try:
                    handler(key_name)
                except Exception as e:
                    log.error(f"[KEYBOARD] 处理按键 {key_name} 时出错: {e}")
            else:
                log.debug(f"[KEYBOARD] 按键 {key_name} 未设置处理函数")

        return True

    def _listen_loop(self):
        """监听循环"""
        try:
            # 创建键盘监听器
            self.listener = keyboard.Listener(on_press=self._on_key_press)
            # 启动监听器
            self.listener.start()

            # 保持监听器运行
            while self.is_running:
                time.sleep(0.1)

        except Exception as e:
            log.error(f"[KEYBOARD] 监听循环出错: {e}")
            log.error(f"[KEYBOARD] Traceback: {traceback.format_exc()}")
        finally:
            if self.listener:
                self.listener.stop()
            self.is_running = False
            log.info("[KEYBOARD] 监听循环已退出")

    def start(self):
        """启动监听服务"""
        if self.is_running:
            log.warning("[KEYBOARD] 监听服务已在运行")
            return

        self.is_running = True
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()
        log.info("[KEYBOARD] 键盘监听服务已启动")

    def stop(self):
        """停止监听服务"""
        if not self.is_running:
            return

        self.is_running = False
        if self.listener:
            self.listener.stop()
        if self.listener_thread:
            self.listener_thread.join(timeout=2)
        log.info("[KEYBOARD] 键盘监听服务已停止")

    def get_status(self) -> Dict:
        """获取服务状态"""
        return {
            "is_running": self.is_running,
            "handlers": list(self.handlers.keys()),
            "platform": platform.system(),
            "supported": True
        }


# 全局键盘监听器实例
_keyboard_listener: Optional[KeyboardListener] = None


def get_keyboard_listener() -> KeyboardListener:
    """获取全局键盘监听器实例"""
    global _keyboard_listener
    if _keyboard_listener is None:
        _keyboard_listener = KeyboardListener()
    return _keyboard_listener


def _get_config_key(key_name: str, suffix: str) -> str:
    """构建配置键名"""
    return f"keyboard.{key_name}.{suffix}"


def create_key_handler(key: str) -> Callable:
    """
    创建按键处理函数
    :param key: 按键名 (F13~F19)
    :return: 处理函数
    """

    def handler(key_name: str):
        url = config_mgr.get(_get_config_key(key_name, "url"))

        if not url:
            log.warning(f"[KEYBOARD] 按键 {key_name} 未配置 URL，跳过")
            return

        method = config_mgr.get(_get_config_key(key_name, "method"), 'GET')
        data_str = config_mgr.get(_get_config_key(key_name, "data"))
        data = _parse_config_data(data_str)

        if data_str and data is None:
            log.warning(f"[KEYBOARD] 按键 {key_name} 的数据格式错误，忽略")

        log.info(f"[KEYBOARD] 按键 {key_name} 触发，发送 {method} 请求到 {url}")
        result = _send_http_request(url, method=method, data=data, headers=None)

        if not result.get("success"):
            log.error(f"[KEYBOARD] 按键 {key_name} 请求失败: {result.get('error')}")

    return handler


def _setup_default_config():
    """设置F12的默认配置"""
    f12_url = config_mgr.get(_get_config_key("F12", "url"))

    if not f12_url:
        # 设置F12的默认配置
        default_url = "http://localhost:8001/keyboard/status"
        config_mgr.set(_get_config_key("F12", "url"), default_url)
        config_mgr.set(_get_config_key("F12", "method"), "GET")
        config_mgr.save_config()
        log.info(f"[KEYBOARD] 已设置F12默认配置: GET {default_url}")


def get_keyboard_status() -> Dict:
    """
    获取键盘监听服务状态和配置
    :return: 状态字典
    """
    listener = get_keyboard_listener()
    status = listener.get_status()

    # 添加配置信息
    config = config_mgr
    configs = {}
    for key in KEY_CODES.keys():
        url = config.get(_get_config_key(key, "url"))
        if url:
            data_str = config.get(_get_config_key(key, "data"))
            data = _parse_config_data(data_str)
            configs[key] = {"method": config.get(_get_config_key(key, "method"), "GET"), "url": url, "data": data}

    status["configs"] = configs
    return status


def start_keyboard_service():
    """
    启动键盘监听服务
    :return: (success: bool, message: str)
    """
    try:
        listener = get_keyboard_listener()
        # 设置所有已配置按键的处理函数
        # 设置F12的默认配置（如果未配置）
        _setup_default_config()

        for key in KEY_CODES.keys():
            url = config_mgr.get(_get_config_key(key, "url"))
            if url:
                handler = create_key_handler(key)
                listener.set_handler(key, handler)
                log.info(f"[KEYBOARD] 已配置按键 {key} -> {url}")

        listener.start()
        return True, "键盘监听服务已启动"
    except Exception as e:
        log.error(f"[KEYBOARD] 启动服务失败: {e}")
        return False, f"启动失败: {str(e)}"


def stop_keyboard_service():
    """
    停止键盘监听服务
    :return: (success: bool, message: str)
    """
    try:
        listener = get_keyboard_listener()
        listener.stop()
        return True, "键盘监听服务已停止"
    except Exception as e:
        log.error(f"[KEYBOARD] 停止服务失败: {e}")
        return False, f"停止失败: {str(e)}"


def _parse_config_data(data_str: str) -> dict:
    """
    解析配置数据
    :param data_str: JSON 字符串
    :return: 解析后的数据，如果解析失败返回 None
    """
    if not data_str:
        return None
    try:
        return json.loads(data_str)
    except json.JSONDecodeError:
        return None


def _build_key_config(key: str) -> dict:
    """
    构建单个按键配置
    :param config: 配置对象
    :param key: 按键名
    :return: 配置字典
    """
    url = config_mgr.get(_get_config_key(key, "url"))
    if not url:
        return {}

    result = {
        "method": config_mgr.get(_get_config_key(key, "method"), "GET"),
        "url": url,
    }

    data_str = config_mgr.get(_get_config_key(key, "data"))
    data = _parse_config_data(data_str)
    if data is not None:
        result["data"] = data

    return result


def get_key_config(key: str = None) -> dict:
    """
    获取按键配置
    :param key: 按键名，如果为 None 则返回所有按键配置
    :return: 配置字典
    """

    if key:
        # 返回单个按键配置
        if key not in KEY_CODES:
            return {}
        return _build_key_config(key)
    else:
        # 返回所有按键配置
        configs = {}
        for k in KEY_CODES.keys():
            key_config = _build_key_config(k)
            if key_config:
                configs[k] = key_config
        return configs


def save_key_config(key: str, url: str, method: str, data: dict = None) -> tuple[bool, str, dict]:
    """
    保存按键配置
    :param key: 按键名
    :param url: 请求 URL
    :param method: HTTP 方法
    :param data: 请求数据
    :return: (success: bool, message: str, config_data: dict)
    """
    try:
        config_mgr.set(_get_config_key(key, "url"), url)
        config_mgr.set(_get_config_key(key, "method"), method)

        # 保存数据（如果有）
        if data:
            config_mgr.set(_get_config_key(key, "data"), json.dumps(data))
        else:
            # 清除旧数据
            if config_mgr.get(_get_config_key(key, "data")):
                config_mgr.set(_get_config_key(key, "data"), "")

        # 保存配置到文件
        if not config_mgr.save_config():
            return False, "保存配置失败", {}

        # 如果服务正在运行，更新处理函数
        listener = get_keyboard_listener()
        if listener.is_running:
            handler = create_key_handler(key)
            listener.set_handler(key, handler)

        log.info(f"[KEYBOARD] 已配置按键 {key}: {method} {url}")

        return True, f"按键 {key} 配置已保存", {"method": method, "url": url, "data": data}
    except Exception as e:
        log.error(f"[KEYBOARD] 配置失败: {e}")
        return False, f"配置失败: {str(e)}", {}


def delete_key_config(key: str) -> tuple[bool, str]:
    """
    删除按键配置
    :param key: 按键名
    :return: (success: bool, message: str)
    """
    try:
        # 删除配置项
        for suffix in ["url", "method", "data"]:
            config_mgr.set(_get_config_key(key, suffix), "")

        # 保存配置到文件
        if not config_mgr.save_config():
            return False, "保存配置失败"

        # 如果服务正在运行，移除处理函数
        listener = get_keyboard_listener()
        if listener.is_running:
            listener.remove_handler(key)

        log.info(f"[KEYBOARD] 已删除按键 {key} 的配置")
        return True, f"按键 {key} 配置已删除"
    except Exception as e:
        log.error(f"[KEYBOARD] 删除配置失败: {e}")
        return False, f"删除失败: {str(e)}"


def simulate_key_press(key: str) -> tuple[bool, str, dict]:
    """
    模拟按键触发
    :param key: 按键名 (F13~F19)
    :return: (success: bool, message: str, result: dict)
    """
    try:
        if key not in KEY_CODES:
            return False, f"不支持的按键: {key}，仅支持 {', '.join(KEY_CODES.keys())}", {}

        listener = get_keyboard_listener()

        # 检查是否有配置该按键的处理函数
        with listener._lock:
            handler = listener.handlers.get(key)

        if not handler:
            # 如果没有处理函数，尝试设置
            url = config_mgr.get(_get_config_key(key, "url"))
            if not url:
                return False, f"按键 {key} 未配置 URL，请先配置", {}

            # 设置处理函数
            handler = create_key_handler(key)
            listener.set_handler(key, handler)

        # 模拟按键触发
        log.info(f"[KEYBOARD] 模拟按键触发: {key}")
        try:
            handler(key)
            return True, f"按键 {key} 模拟触发成功", {}
        except Exception as e:
            log.error(f"[KEYBOARD] 模拟按键 {key} 触发失败: {e}")
            return False, f"触发失败: {str(e)}", {}

    except Exception as e:
        log.error(f"[KEYBOARD] 模拟按键失败: {e}")
        return False, f"模拟失败: {str(e)}", {}
