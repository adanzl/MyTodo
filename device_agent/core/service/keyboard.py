'''
键盘监听服务
监听所有按键并输出日志，F12~F19 按键可配置发送 HTTP 请求
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

log = root_logger()

# ==================== 库导入 ====================
PYNPUT_AVAILABLE = False
keyboard = None
try:
    from pynput import keyboard  # pyright: ignore[reportMissingModuleSource]
    PYNPUT_AVAILABLE = True
except ImportError:
    pass

EVDEV_AVAILABLE = False
evdev = None
try:
    import evdev  # pyright: ignore[reportMissingImports]
    EVDEV_AVAILABLE = True
except ImportError:
    pass

# ==================== 常量定义 ====================
# F12~F19 按键名列表
KEY_NAMES = [f'F{i}' for i in range(12, 20)]

# 向后兼容：KEY_CODES 字典（用于 API 验证）
KEY_CODES = {name: name for name in KEY_NAMES}

# 配置键后缀
CONFIG_SUFFIXES = ["url", "method", "data"]

# 默认 HTTP 方法
DEFAULT_HTTP_METHOD = "GET"

# 默认 F12 URL
DEFAULT_F12_URL = "http://localhost:8000/keyboard/status"

# 线程等待超时时间（秒）
THREAD_JOIN_TIMEOUT = 2

# pynput 监听循环休眠间隔（秒）
PYNPUT_SLEEP_INTERVAL = 0.1

# evdev 按键按下事件值
EVDEV_KEY_PRESS_VALUE = 1

# evdev 设备重连间隔（秒）
EVDEV_RECONNECT_INTERVAL = 2

# evdev 设备重连最大尝试次数（0 表示无限重试）
EVDEV_MAX_RECONNECT_ATTEMPTS = 0

# pynput 按键映射（如果可用）
PYNPUT_KEY_CODES: Dict[str, object] = {}
PYNPUT_KEY_TO_NAME: Dict[object, str] = {}
if PYNPUT_AVAILABLE and keyboard:
    PYNPUT_KEY_CODES = {f'F{i}': getattr(keyboard.Key, f'f{i}', None) for i in range(12, 20)}
    PYNPUT_KEY_CODES = {k: v for k, v in PYNPUT_KEY_CODES.items() if v is not None}
    PYNPUT_KEY_TO_NAME = {v: k for k, v in PYNPUT_KEY_CODES.items() if v is not None}

# evdev 按键码映射（Linux 键盘扫描码）
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


# ==================== 工具函数 ====================
def _get_config_key(key_name: str, suffix: str) -> str:
    """构建配置键名"""
    return f"keyboard.{key_name}.{suffix}"


# URL 构建缓存
_base_url_cache: Optional[str] = None


def _get_base_url() -> Optional[str]:
    """获取并缓存 center_server_url 的基础 URL"""
    global _base_url_cache
    if _base_url_cache is None:
        base_url = config_mgr.get('center_server_url', '').strip()
        if base_url:
            # 移除末尾的斜杠
            _base_url_cache = base_url.rstrip('/')
    return _base_url_cache


def _clear_base_url_cache():
    """清除 base_url 缓存（用于配置更新后）"""
    global _base_url_cache
    _base_url_cache = None


def _build_full_url(url: str) -> Optional[str]:
    """
    构建完整的 URL
    :param url: 配置的 URL（可能是完整 URL 或路径）
    :return: 完整的 URL，如果无法构建则返回 None
    """
    if not url:
        return None

    url = url.strip()

    # 如果以 http:// 或 https:// 开头，则认为是完整 URL
    if url.startswith(('http://', 'https://')):
        return url

    # 否则，作为路径与 center_server_url 拼接
    base_url = _get_base_url()
    if not base_url:
        log.warning(f"[KEYBOARD] center_server_url 未配置，无法构建完整 URL: {url}")
        return None

    # 确保 url 以 / 开头
    if not url.startswith('/'):
        url = '/' + url

    return f"{base_url}{url}"


def _parse_config_data(data_str: str) -> Dict:
    """
    解析配置数据
    :param data_str: JSON 字符串
    :return: 解析后的数据，如果解析失败返回 {}
    """
    if not data_str:
        return {}
    try:
        return json.loads(data_str)
    except json.JSONDecodeError:
        log.warning(f"[KEYBOARD] 数据格式错误，忽略: {data_str}")
    return {}


def _get_key_config_raw(key: str) -> Optional[Dict[str, str]]:
    """
    获取按键的原始配置（不构建 URL）
    :param key: 按键名
    :return: 配置字典，包含 url, method, data，如果未配置则返回 None
    """
    url_config = config_mgr.get(_get_config_key(key, "url"))
    if not url_config:
        return None

    return {
        "url": url_config,
        "method": config_mgr.get(_get_config_key(key, "method"), DEFAULT_HTTP_METHOD),
        "data": config_mgr.get(_get_config_key(key, "data"), "")
    }


def _get_key_config(key: str) -> Optional[Dict]:
    """
    获取按键配置（构建完整 URL）
    :param key: 按键名
    :return: 配置字典，包含 method, url（完整URL）, data，如果未配置或 URL 构建失败则返回 None
    """
    raw_config = _get_key_config_raw(key)
    if not raw_config:
        return None

    # 构建完整 URL
    full_url = _build_full_url(raw_config["url"])
    if not full_url:
        return None

    result = {
        "method": raw_config["method"],
        "url": full_url,
    }

    # 解析数据
    data = _parse_config_data(raw_config["data"])
    if data:
        result["data"] = data

    return result


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

        # 将按键转换为字符串名称
        try:
            if hasattr(key, 'name'):
                # 特殊按键（如 Key.f12）
                key_name = key.name
            elif hasattr(key, 'char') and key.char:
                # 普通字符按键
                key_name = key.char
            else:
                # 其他情况，尝试转换为字符串
                key_name = str(key)
            
            # 输出日志
            log.info(f"[KEYBOARD] 按键按下: {key_name}")
            
            # 如果是 F12~F19，触发对应的处理函数
            if key in PYNPUT_KEY_TO_NAME:
                key_name_mapped = PYNPUT_KEY_TO_NAME[key]
                self._trigger_handler(key_name_mapped)
        except Exception as e:
            log.error(f"[KEYBOARD] 处理按键事件时出错: {e}")
        
        return True

    def _on_key_press_evdev(self, key_code: int):
        """evdev 按键按下事件处理"""
        if not self.is_running:
            return

        # 获取按键名称
        try:
            if EVDEV_AVAILABLE:
                # 尝试从 evdev.ecodes.KEY 获取按键名称（反向映射字典）
                if hasattr(evdev.ecodes, 'KEY') and key_code in evdev.ecodes.KEY:
                    key_name = evdev.ecodes.KEY[key_code]
                    # 移除 KEY_ 前缀（如果存在）
                    if key_name.startswith('KEY_'):
                        key_name = key_name[4:]
                else:
                    key_name = f"UNKNOWN_{key_code}"
            else:
                key_name = f"KEY_{key_code}"
            
            # 输出日志
            log.info(f"[KEYBOARD] 按键按下: {key_name} (code: {key_code})")
            
            # 如果是 F12~F19，触发对应的处理函数
            if key_code in EVDEV_KEY_TO_NAME:
                key_name_mapped = EVDEV_KEY_TO_NAME[key_code]
                self._trigger_handler(key_name_mapped)
        except Exception as e:
            log.error(f"[KEYBOARD] 处理按键事件时出错: {e}")

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
                time.sleep(PYNPUT_SLEEP_INTERVAL)
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
        """evdev 监听循环（支持设备热插拔）"""
        reconnect_count = 0
        permanent_error = False
        
        while self.is_running and not permanent_error:
            device = None
            try:
                # 每次循环都重新查找设备（支持热插拔）
                device_path = _find_keyboard_device()
                if not device_path:
                    if reconnect_count == 0:
                        log.warning("[KEYBOARD] 未找到键盘设备，等待设备插入...")
                    reconnect_count += 1
                    
                    # 检查是否超过最大重连次数
                    if EVDEV_MAX_RECONNECT_ATTEMPTS > 0 and reconnect_count > EVDEV_MAX_RECONNECT_ATTEMPTS:
                        log.error(f"[KEYBOARD] 已达到最大重连次数 ({EVDEV_MAX_RECONNECT_ATTEMPTS})，停止监听")
                        permanent_error = True
                        break
                    
                    # 等待一段时间后重试
                    for _ in range(int(EVDEV_RECONNECT_INTERVAL * 10)):
                        if not self.is_running:
                            return
                        time.sleep(0.1)
                    continue

                # 找到设备，重置重连计数
                if reconnect_count > 0:
                    log.info(f"[KEYBOARD] 检测到键盘设备已插入: {device_path}")
                    reconnect_count = 0
                    self._evdev_device_path = device_path

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
                    if event.type == evdev.ecodes.EV_KEY and event.value == EVDEV_KEY_PRESS_VALUE:
                        self._on_key_press_evdev(event.code)

            except PermissionError:
                log.error("[KEYBOARD] 权限不足，无法访问键盘设备。请使用 root 运行或添加用户到 input 组: sudo usermod -a -G input $USER")
                permanent_error = True
                break
            except OSError as e:
                # 设备断开或不可用，尝试重连
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['no such file', 'no such device', 'device disconnected', 'input/output error']):
                    log.warning(f"[KEYBOARD] 键盘设备已断开: {e}，尝试重新连接...")
                    reconnect_count += 1
                    
                    # 检查是否超过最大重连次数
                    if EVDEV_MAX_RECONNECT_ATTEMPTS > 0 and reconnect_count > EVDEV_MAX_RECONNECT_ATTEMPTS:
                        log.error(f"[KEYBOARD] 已达到最大重连次数 ({EVDEV_MAX_RECONNECT_ATTEMPTS})，停止监听")
                        permanent_error = True
                        break
                    
                    # 清理设备引用
                    if device:
                        try:
                            device.ungrab()
                        except Exception:
                            pass
                    
                    # 清除设备路径，下次循环会重新查找
                    self._evdev_device_path = None
                    
                    # 等待一段时间后重试
                    for _ in range(int(EVDEV_RECONNECT_INTERVAL * 10)):
                        if not self.is_running:
                            return
                        time.sleep(0.1)
                else:
                    # 其他 OSError，可能是永久性错误
                    log.error(f"[KEYBOARD] 设备访问错误: {e}")
                    permanent_error = True
                    break
            except Exception as e:
                log.error(f"[KEYBOARD] evdev 监听循环出错: {e}")
                log.error(f"[KEYBOARD] Traceback: {traceback.format_exc()}")
                permanent_error = True
                break
            finally:
                if device:
                    try:
                        device.ungrab()
                    except Exception:
                        pass
        
        self.is_running = False
        log.info("[KEYBOARD] evdev 监听循环已退出")

    def _try_start_evdev(self) -> bool:
        """尝试启动 evdev 监听"""
        if platform.system() != 'Linux' or not EVDEV_AVAILABLE:
            return False

        if not self._evdev_device_path:
            self._evdev_device_path = _find_keyboard_device()

        if self._evdev_device_path:
            self._listen_loop_evdev()
            return True
        else:
            log.error("[KEYBOARD] 未找到可用的键盘设备")
            self.is_running = False
            return False

    def _listen_loop(self):
        """监听循环（自动选择 pynput 或 evdev）"""
        # 如果已指定使用 evdev，直接使用
        if self._use_evdev:
            if not self._try_start_evdev():
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
                display_keywords = ['NoDisplay', 'DISPLAY', 'X11']
                if any(keyword in error_msg for keyword in display_keywords):
                    log.info("[KEYBOARD] pynput 需要图形界面，切换到 evdev 模式")
                else:
                    log.warning(f"[KEYBOARD] pynput 启动失败: {e}，尝试 evdev")
                self._use_evdev = True

        # 如果 pynput 失败，尝试使用 evdev（仅 Linux）
        if self._use_evdev:
            self._try_start_evdev()
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
            self.listener_thread.join(timeout=THREAD_JOIN_TIMEOUT)
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




# ==================== 全局实例管理 ====================
_keyboard_listener: Optional[KeyboardListener] = None


def get_keyboard_listener() -> KeyboardListener:
    """获取全局键盘监听器实例"""
    global _keyboard_listener
    if _keyboard_listener is None:
        _keyboard_listener = KeyboardListener()
    return _keyboard_listener


def create_key_handler(key: str) -> Callable:
    """
    创建按键处理函数
    :param key: 按键名 (F13~F19)
    :return: 处理函数
    """

    def handler(key_name: str):
        config = _get_key_config(key_name)
        if not config:
            log.warning(f"[KEYBOARD] 按键 {key_name} 未配置或 URL 构建失败，跳过")
            return

        # 准备请求数据
        data = config.get("data", {}).copy()
        data.update({
            "key": key_name,
            "value": 1,
            "action": "keyboard"
        })

        url = config["url"]
        method = config["method"]
        log.info(f"[KEYBOARD] 按键 {key_name} 触发，发送 {method} 请求到 {url}")
        result = _send_http_request(url, method=method, data=data, headers=None)

        if not result.get("success"):
            log.error(f"[KEYBOARD] 按键 {key_name} 请求失败: {result.get('error')}")

    return handler


def _setup_default_config():
    """设置F12的默认配置"""
    if not config_mgr.get(_get_config_key("F12", "url")):
        config_mgr.set(_get_config_key("F12", "url"), DEFAULT_F12_URL)
        config_mgr.set(_get_config_key("F12", "method"), DEFAULT_HTTP_METHOD)
        config_mgr.save_config()
        log.info(f"[KEYBOARD] 已设置F12默认配置: {DEFAULT_HTTP_METHOD} {DEFAULT_F12_URL}")


def get_keyboard_status() -> Dict:
    """
    获取键盘监听服务状态和配置
    :return: 状态字典
    """
    listener = get_keyboard_listener()
    status = listener.get_status()

    # 添加配置信息
    configs = {}
    for key in KEY_NAMES:
        key_config = _get_key_config(key)
        if key_config:
            configs[key] = {
                "method": key_config["method"],
                "url": key_config["url"],
                "data": key_config.get("data", {})
            }

    status["configs"] = configs
    return status


def start_keyboard_service() -> Tuple[bool, str]:
    """
    启动键盘监听服务
    :return: (success: bool, message: str)
    """
    try:
        log.info(f"===== [Start keyboard service] =====")
        listener = get_keyboard_listener()
        # 设置所有已配置按键的处理函数
        # 设置F12的默认配置（如果未配置）
        _setup_default_config()

        for key in KEY_NAMES:
            key_config = _get_key_config(key)
            if key_config:
                handler = create_key_handler(key)
                listener.set_handler(key, handler)
                log.info(f"[KEYBOARD] 已配置按键 {key} -> {key_config['url']}")

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


def _build_key_config(key: str) -> Dict:
    """
    构建单个按键配置
    :param key: 按键名
    :return: 配置字典
    """
    return _get_key_config(key) or {}


def get_key_config(key: Optional[str] = None) -> Dict:
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

        # 清除 URL 缓存（因为可能更新了 center_server_url）
        _clear_base_url_cache()

        # 保存配置到文件
        if not config_mgr.save_config():
            return False, "保存配置失败", {}

        # 如果服务正在运行，更新处理函数
        listener = get_keyboard_listener()
        if listener.is_running:
            handler = create_key_handler(key)
            listener.set_handler(key, handler)

        # 构建完整 URL 用于日志和返回
        full_url = _build_full_url(url)
        if full_url:
            log.info(f"[KEYBOARD] 已配置按键 {key}: {method} {full_url}")
            return True, f"按键 {key} 配置已保存", {"method": method, "url": full_url, "data": data}
        else:
            log.warning(f"[KEYBOARD] 已保存按键 {key} 配置，但 URL 构建失败（请检查 center_server_url 配置）")
            return True, f"按键 {key} 配置已保存（URL: {url}）", {"method": method, "url": url, "data": data}
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
        for suffix in CONFIG_SUFFIXES:
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
            key_config = _get_key_config(key)
            if not key_config:
                return False, f"按键 {key} 未配置 URL 或 URL 构建失败（请检查 center_server_url 配置）", {}

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
