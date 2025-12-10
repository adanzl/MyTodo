'''
键盘监听服务
监听 F12~F19 按键并发送 HTTP 请求
'''
import json
import os
import platform
import threading
import time
import traceback
from typing import Dict, Optional, Callable, Tuple
from core.log_config import root_logger
from core.config import config_mgr
from core.utils import _send_http_request

PYNPUT_AVAILABLE = False
keyboard = None
# 尝试导入 pynput（跨平台）
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    pass
# 尝试导入 evdev（仅 Linux）
EVDEV_AVAILABLE = False
evdev = None
try:
    import evdev  # pyright: ignore[reportMissingImports]
    EVDEV_AVAILABLE = True
except ImportError:
    pass

log = root_logger()

# F12~F19 按键名列表
KEY_NAMES = [f'F{i}' for i in range(12, 20)]

# 向后兼容：KEY_CODES 字典（用于 API 验证）
KEY_CODES = {name: name for name in KEY_NAMES}

# pynput 按键映射（如果可用）
PYNPUT_KEY_CODES = {}
PYNPUT_KEY_TO_NAME = {}
if PYNPUT_AVAILABLE and keyboard:
    PYNPUT_KEY_CODES = {f'F{i}': getattr(keyboard.Key, f'f{i}', None) for i in range(12, 20)}
    PYNPUT_KEY_CODES = {k: v for k, v in PYNPUT_KEY_CODES.items() if v is not None}
    PYNPUT_KEY_TO_NAME = {v: k for k, v in PYNPUT_KEY_CODES.items() if v is not None}

# evdev 按键码映射（Linux 键盘扫描码）
# F12-F19 对应的 Linux 输入事件键码
EVDEV_KEY_CODES: Dict[str, int] = {}
EVDEV_KEY_TO_NAME: Dict[int, str] = {}

if EVDEV_AVAILABLE:
    EVDEV_KEY_CODES = {
        'F12': evdev.ecodes.KEY_F12,
        'F13': evdev.ecodes.KEY_F13,
        'F14': evdev.ecodes.KEY_F14,
        'F15': evdev.ecodes.KEY_F15,
        'F16': evdev.ecodes.KEY_F16,
        'F17': evdev.ecodes.KEY_F17,
        'F18': evdev.ecodes.KEY_F18,
        'F19': evdev.ecodes.KEY_F19,
    }

    EVDEV_KEY_TO_NAME = {v: k for k, v in EVDEV_KEY_CODES.items()}


def _find_keyboard_device() -> Optional[str]:
    """
    查找可用的键盘设备（Linux evdev）
    :return: 设备路径，如果未找到则返回 None
    """
    if not EVDEV_AVAILABLE:
        return None

    try:
        # 查找所有输入设备
        device_paths = evdev.list_devices()
        if not device_paths:
            log.warning("[KEYBOARD] 未找到任何输入设备")
            return None

        devices = []
        for path in device_paths:
            try:
                device = evdev.InputDevice(path)
                devices.append(device)
            except (OSError, PermissionError) as e:
                log.debug(f"[KEYBOARD] 无法打开设备 {path}: {e}")
                continue

        # 优先查找支持 F12-F19 的键盘设备
        for device in devices:
            if evdev.ecodes.EV_KEY not in device.capabilities():
                continue

            key_codes = device.capabilities().get(evdev.ecodes.EV_KEY, [])
            if any(code in key_codes for code in EVDEV_KEY_CODES.values()):
                log.info(f"[KEYBOARD] 找到支持 F12-F19 的键盘设备: {device.path} ({device.name})")
                return device.path

        # 如果没找到支持 F12-F19 的设备，使用第一个键盘设备
        for device in devices:
            if evdev.ecodes.EV_KEY in device.capabilities():
                log.info(f"[KEYBOARD] 使用键盘设备: {device.path} ({device.name})")
                return device.path

        log.warning("[KEYBOARD] 未找到可用的键盘设备")
        return None
    except Exception as e:
        log.warning(f"[KEYBOARD] 查找键盘设备失败: {e}")
        return None


class KeyboardListener:
    """键盘监听器"""

    def __init__(self):
        self.is_running = False
        self.listener_thread: Optional[threading.Thread] = None
        self.listener: Optional[object] = None  # pynput keyboard.Listener 或 evdev InputDevice
        self.handlers: Dict[str, Callable] = {}  # 按键名 -> 处理函数
        self._lock = threading.Lock()
        self._use_evdev = False  # 是否使用 evdev
        self._evdev_device_path: Optional[str] = None

    def set_handler(self, key: str, handler: Callable):
        """
        设置按键处理函数
        :param key: 按键名 (F12~F19)
        :param handler: 处理函数，接收按键名作为参数
        """
        if key not in KEY_NAMES:
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

    def _on_key_press_pynput(self, key):
        """pynput 按键按下事件处理"""
        if not self.is_running:
            return False

        # 检查是否是 F12~F19
        if key in PYNPUT_KEY_TO_NAME:
            key_name = PYNPUT_KEY_TO_NAME[key]
            self._trigger_handler(key_name)
        return True

    def _on_key_press_evdev(self, key_code: int):
        """evdev 按键按下事件处理"""
        if not self.is_running:
            return

        if key_code in EVDEV_KEY_TO_NAME:
            key_name = EVDEV_KEY_TO_NAME[key_code]
            self._trigger_handler(key_name)

    def _trigger_handler(self, key_name: str):
        """触发按键处理函数"""
        with self._lock:
            handler = self.handlers.get(key_name)

        if handler:
            try:
                handler(key_name)
            except Exception as e:
                log.error(f"[KEYBOARD] 处理按键 {key_name} 时出错: {e}")
        else:
            log.debug(f"[KEYBOARD] 按键 {key_name} 未设置处理函数")

    def _listen_loop_pynput(self):
        """pynput 监听循环"""
        try:
            self.listener = keyboard.Listener(on_press=self._on_key_press_pynput)
            self.listener.start()

            while self.is_running:
                time.sleep(0.1)
        except Exception as e:
            log.error(f"[KEYBOARD] pynput 监听循环出错: {e}")
            log.error(f"[KEYBOARD] Traceback: {traceback.format_exc()}")
        finally:
            if self.listener:
                try:
                    self.listener.stop()
                except Exception:
                    pass
            self.is_running = False
            log.info("[KEYBOARD] pynput 监听循环已退出")

    def _listen_loop_evdev(self):
        """evdev 监听循环"""
        device = None
        try:
            device_path = self._evdev_device_path
            if not device_path:
                log.error("[KEYBOARD] 未找到键盘设备")
                return

            device = evdev.InputDevice(device_path)
            log.info(f"[KEYBOARD] 开始监听设备: {device.path} ({device.name})")

            # 将设备设置为独占模式（需要权限）
            try:
                device.grab()
                log.debug("[KEYBOARD] 设备已独占锁定")
            except (PermissionError, OSError) as e:
                log.warning(f"[KEYBOARD] 无法独占锁定设备（可能需要 root 权限或 input 组）: {e}")

            # 监听事件
            for event in device.read_loop():
                if not self.is_running:
                    break

                # 只处理按键按下事件 (value=1 表示按下，0=释放，2=长按)
                if event.type == evdev.ecodes.EV_KEY and event.value == 1:
                    self._on_key_press_evdev(event.code)

        except PermissionError:
            log.error("[KEYBOARD] 权限不足，无法访问键盘设备。请使用 root 运行或添加用户到 input 组: sudo usermod -a -G input $USER")
        except OSError as e:
            log.error(f"[KEYBOARD] 设备访问错误: {e}")
        except Exception as e:
            log.error(f"[KEYBOARD] evdev 监听循环出错: {e}")
            log.error(f"[KEYBOARD] Traceback: {traceback.format_exc()}")
        finally:
            if device:
                try:
                    device.ungrab()
                except Exception:
                    pass
            self.is_running = False
            log.info("[KEYBOARD] evdev 监听循环已退出")

    def _listen_loop(self):
        """监听循环（自动选择 pynput 或 evdev）"""
        # 如果已指定使用 evdev，直接使用
        if self._use_evdev:
            if platform.system() == 'Linux' and EVDEV_AVAILABLE:
                if not self._evdev_device_path:
                    self._evdev_device_path = _find_keyboard_device()
                if self._evdev_device_path:
                    self._listen_loop_evdev()
                else:
                    log.error("[KEYBOARD] 未找到可用的键盘设备")
                    self.is_running = False
            else:
                log.error("[KEYBOARD] evdev 不可用")
                self.is_running = False
            return

        # 尝试使用 pynput
        if PYNPUT_AVAILABLE:
            try:
                self._listen_loop_pynput()
                return
            except Exception as e:
                error_msg = str(e)
                # 如果是无 DISPLAY 错误，尝试 evdev
                if any(keyword in error_msg for keyword in ['NoDisplay', 'DISPLAY', 'X11']):
                    log.info("[KEYBOARD] pynput 需要图形界面，切换到 evdev 模式")
                    self._use_evdev = True
                else:
                    log.warning(f"[KEYBOARD] pynput 启动失败: {e}，尝试 evdev")
                    self._use_evdev = True

        # 如果 pynput 失败，尝试使用 evdev（仅 Linux）
        if self._use_evdev and platform.system() == 'Linux' and EVDEV_AVAILABLE:
            if not self._evdev_device_path:
                self._evdev_device_path = _find_keyboard_device()
            if self._evdev_device_path:
                self._listen_loop_evdev()
            else:
                log.error("[KEYBOARD] 未找到可用的键盘设备")
                self.is_running = False
        elif not PYNPUT_AVAILABLE and not EVDEV_AVAILABLE:
            log.error("[KEYBOARD] 无法启动键盘监听：pynput 和 evdev 都不可用")
            self.is_running = False

    def start(self):
        """启动监听服务"""
        if self.is_running:
            log.warning("[KEYBOARD] 监听服务已在运行")
            return

        # 在 Linux 上，如果没有 DISPLAY，尝试使用 evdev
        if platform.system() == 'Linux' and not os.environ.get('DISPLAY'):
            if EVDEV_AVAILABLE:
                self._use_evdev = True
                self._evdev_device_path = _find_keyboard_device()
                if not self._evdev_device_path:
                    log.warning("[KEYBOARD] 无桌面环境且未找到键盘设备，键盘监听可能不可用")
            else:
                log.warning("[KEYBOARD] 无桌面环境且 evdev 不可用，请安装 python-evdev")

        self.is_running = True
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()

        mode = "evdev" if self._use_evdev else "pynput"
        log.info(f"[KEYBOARD] 键盘监听服务已启动（模式: {mode}）")

    def stop(self):
        """停止监听服务"""
        if not self.is_running:
            return

        self.is_running = False

        # 停止监听器
        if self.listener:
            try:
                if self._use_evdev and hasattr(self.listener, 'ungrab'):
                    # evdev 设备
                    self.listener.ungrab()
                elif not self._use_evdev:
                    # pynput listener
                    self.listener.stop()
            except Exception as e:
                log.debug(f"[KEYBOARD] 停止监听器时出错（可忽略）: {e}")

        # 等待线程结束
        if self.listener_thread:
            self.listener_thread.join(timeout=2)
            if self.listener_thread.is_alive():
                log.warning("[KEYBOARD] 监听线程未在超时时间内结束")

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
        default_url = "http://localhost:8000/keyboard/status"
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
    for key in KEY_NAMES:
        url = config.get(_get_config_key(key, "url"))
        if url:
            data_str = config.get(_get_config_key(key, "data"))
            data = _parse_config_data(data_str)
            configs[key] = {"method": config.get(_get_config_key(key, "method"), "GET"), "url": url, "data": data}

    status["configs"] = configs
    return status


def start_keyboard_service() -> Tuple[bool, str]:
    """
    启动键盘监听服务
    :return: (success: bool, message: str)
    """
    try:
        listener = get_keyboard_listener()
        # 设置所有已配置按键的处理函数
        # 设置F12的默认配置（如果未配置）
        _setup_default_config()

        for key in KEY_NAMES:
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


def stop_keyboard_service() -> Tuple[bool, str]:
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
        if key not in KEY_NAMES:
            return {}
        return _build_key_config(key)
    else:
        # 返回所有按键配置
        configs = {}
        for k in KEY_NAMES:
            key_config = _build_key_config(k)
            if key_config:
                configs[k] = key_config
        return configs


def save_key_config(key: str, url: str, method: str, data: dict = None) -> Tuple[bool, str, dict]:
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


def delete_key_config(key: str) -> Tuple[bool, str]:
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


def simulate_key_press(key: str) -> Tuple[bool, str, dict]:
    """
    模拟按键触发
    :param key: 按键名 (F13~F19)
    :return: (success: bool, message: str, result: dict)
    """
    try:
        if key not in KEY_NAMES:
            return False, f"不支持的按键: {key}，仅支持 {', '.join(KEY_NAMES)}", {}

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
