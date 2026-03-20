'''
键盘硬件设备层
封装 pynput 和 evdev 底层键盘监听功能
'''
import os
import platform
import threading
import time
import traceback
from typing import Optional, Callable, Dict, Union, Any

from core.log_config import root_logger

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
KEY_NAMES = [f'F{i}' for i in range(12, 20)]

# pynput 按键映射
PYNPUT_KEY_CODES: Dict[str, object] = {}
PYNPUT_KEY_TO_NAME: Dict[object, str] = {}
if PYNPUT_AVAILABLE and keyboard:
    PYNPUT_KEY_CODES = {f'F{i}': getattr(keyboard.Key, f'f{i}', None) for i in range(12, 20)}
    PYNPUT_KEY_CODES = {k: v for k, v in PYNPUT_KEY_CODES.items() if v is not None}
    PYNPUT_KEY_TO_NAME = {v: k for k, v in PYNPUT_KEY_CODES.items() if v is not None}

# evdev 按键码映射（Linux 键盘扫描码）
EVDEV_KEY_CODES: Dict[str, int] = {}
EVDEV_KEY_TO_NAME: Dict[int, str] = {}
if EVDEV_AVAILABLE and evdev:
    EVDEV_KEY_CODES = {
        'F12': evdev.ecodes.KEY_F12,  # pyright: ignore[reportOptionalMemberAccess]
        'F13': evdev.ecodes.KEY_F13,  # pyright: ignore[reportOptionalMemberAccess]
        'F14': evdev.ecodes.KEY_F14,  # pyright: ignore[reportOptionalMemberAccess]
        'F15': evdev.ecodes.KEY_F15,  # pyright: ignore[reportOptionalMemberAccess]
        'F16': evdev.ecodes.KEY_F16,  # pyright: ignore[reportOptionalMemberAccess]
        'F17': evdev.ecodes.KEY_F17,  # pyright: ignore[reportOptionalMemberAccess]
        'F18': evdev.ecodes.KEY_F18,  # pyright: ignore[reportOptionalMemberAccess]
        'F19': evdev.ecodes.KEY_F19,  # pyright: ignore[reportOptionalMemberAccess]
    }
    EVDEV_KEY_TO_NAME = {v: k for k, v in EVDEV_KEY_CODES.items()}

# evdev 按键按下事件值
EVDEV_KEY_PRESS_VALUE = 1

# evdev 设备重连间隔（秒）
EVDEV_RECONNECT_INTERVAL = 2

# evdev 设备重连最大尝试次数（0 表示无限重试）
EVDEV_MAX_RECONNECT_ATTEMPTS = 0

# pynput 监听循环休眠间隔（秒）
PYNPUT_SLEEP_INTERVAL = 0.1

# 线程等待超时时间（秒）
THREAD_JOIN_TIMEOUT = 2


class KeyboardDev:
    """键盘硬件设备类，负责底层键盘事件监听"""
    
    def __init__(self):
        log.info("[KEYBOARD_DEV] KeyboardDev init")
        self.is_running = False
        self.listener = None  # pynput Listener 或 evdev InputDevice
        self._on_press_callback: Optional[Callable] = None
        self._use_evdev = False
        self._evdev_device_path: Optional[str] = None
    
    def set_on_press_handler(self, callback: Callable):
        """
        设置按键按下事件回调
        :param callback: 回调函数，接收按键名称作为参数
        """
        self._on_press_callback = callback
    
    def _on_key_press_pynput(self, key):
        """pynput 按键按下事件处理"""
        if not self.is_running:
            return
        
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
            log.info(f"[KEYBOARD] 按键按下：{key_name}")
                    
            # 如果是 F12~F19，触发回调
            if key in PYNPUT_KEY_TO_NAME:
                key_name_mapped = PYNPUT_KEY_TO_NAME[key]
                if self._on_press_callback:
                    self._on_press_callback(key_name_mapped)
        except Exception as e:
            log.error(f"[KEYBOARD] 处理按键事件时出错：{e}")
    
    def _on_key_press_evdev(self, key_code: int):
        """evdev 按键按下事件处理"""
        if not self.is_running:
            return
        
        # 获取按键名称
        try:
            if EVDEV_AVAILABLE and evdev:
                # 尝试从 evdev.ecodes.KEY 获取按键名称（反向映射字典）
                if hasattr(evdev.ecodes, 'KEY') and key_code in evdev.ecodes.KEY:  # pyright: ignore[reportOptionalMemberAccess]
                    key_name = evdev.ecodes.KEY[key_code]  # pyright: ignore[reportOptionalMemberAccess]
                    # 移除 KEY_ 前缀（如果存在）
                    if key_name.startswith('KEY_'):
                        key_name = key_name[4:]
                else:
                    key_name = f"UNKNOWN_{key_code}"
            else:
                key_name = f"KEY_{key_code}"
            
            # 输出日志
            log.info(f"[KEYBOARD] 按键按下：{key_name} (code: {key_code})")
            
            # 如果是 F12~F19，触发回调
            if key_code in EVDEV_KEY_TO_NAME:
                key_name_mapped = EVDEV_KEY_TO_NAME[key_code]
                if self._on_press_callback:
                    self._on_press_callback(key_name_mapped)
        except Exception as e:
            log.error(f"[KEYBOARD] 处理按键事件时出错：{e}")
    
    def _listen_loop_pynput(self):
        """pynput 监听循环"""
        try:
            if keyboard:
                listener_obj = keyboard.Listener(on_press=self._on_key_press_pynput)  # pyright: ignore[reportOptionalMemberAccess]
                if listener_obj:
                    self.listener = listener_obj
                    self.listener.start()  # pyright: ignore[reportOptionalMemberAccess]
    
            while self.is_running:
                time.sleep(PYNPUT_SLEEP_INTERVAL)
        except Exception as e:
            log.error(f"[KEYBOARD] pynput 监听循环出错：{e}")
            log.error(f"[KEYBOARD] Traceback: {traceback.format_exc()}")
        finally:
            if self.listener:
                try:
                    if hasattr(self.listener, 'stop'):
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
                device_path = self._find_keyboard_device()
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
                    log.info(f"[KEYBOARD] 检测到键盘设备已插入：{device_path}")
                    reconnect_count = 0
                    self._evdev_device_path = device_path
                
                device = evdev.InputDevice(device_path)  # pyright: ignore[reportOptionalMemberAccess]
                log.info(f"[KEYBOARD] 开始监听设备：{device.path} ({device.name})")
                
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
                    if event.type == evdev.ecodes.EV_KEY and event.value == EVDEV_KEY_PRESS_VALUE:  # pyright: ignore[reportOptionalMemberAccess]
                        self._on_key_press_evdev(event.code)
                
            except PermissionError:
                log.error("[KEYBOARD] 权限不足，无法访问键盘设备。请使用 root 运行或添加用户到 input 组：sudo usermod -a -G input $USER")
                permanent_error = True
                break
            except OSError as e:
                # 设备断开或不可用，尝试重连
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['no such file', 'no such device', 'device disconnected', 'input/output error']):
                    log.warning(f"[KEYBOARD] 键盘设备已断开：{e}，尝试重新连接...")
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
                    log.error(f"[KEYBOARD] 设备访问错误：{e}")
                    permanent_error = True
                    break
            except Exception as e:
                log.error(f"[KEYBOARD] evdev 监听循环出错：{e}")
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
    
    def _find_keyboard_device(self) -> Optional[str]:
        """
        查找可用的键盘设备（Linux evdev）
        :return: 设备路径，如果未找到则返回 None
        """
        if not EVDEV_AVAILABLE:
            return None
        
        try:
            # 查找所有输入设备
            device_paths = evdev.list_devices()  # pyright: ignore[reportOptionalMemberAccess]
            if not device_paths:
                log.warning("[KEYBOARD] 未找到任何输入设备")
                return None
            
            devices = []
            for path in device_paths:
                try:
                    device = evdev.InputDevice(path)  # pyright: ignore[reportOptionalMemberAccess]
                    devices.append(device)
                except (OSError, PermissionError) as e:
                    log.debug(f"[KEYBOARD] 无法打开设备 {path}: {e}")
                    continue
            
            # 优先查找支持 F12-F19 的键盘设备
            for device in devices:
                if evdev.ecodes.EV_KEY not in device.capabilities():  # pyright: ignore[reportOptionalMemberAccess]
                    continue
            
                key_codes = device.capabilities().get(evdev.ecodes.EV_KEY, [])  # pyright: ignore[reportOptionalMemberAccess]
                if any(code in key_codes for code in EVDEV_KEY_CODES.values()):
                    log.info(f"[KEYBOARD] 找到支持 F12-F19 的键盘设备：{device.path} ({device.name})")
                    return device.path
            
            # 未找到支持 F12-F19 的键盘设备时，不再退化为"任意 EV_KEY 设备"，
            # 避免错误地将红外遥控等设备当成键盘，从而导致重连后设备不正确。
            log.warning("[KEYBOARD] 未找到支持 F12-F19 的键盘设备，等待真实键盘插入")
            return None
        except Exception as e:
            log.warning(f"[KEYBOARD] 查找键盘设备失败：{e}")
            return None
    
    def _try_start_evdev(self) -> bool:
        """尝试启动 evdev 监听"""
        if platform.system() != 'Linux' or not EVDEV_AVAILABLE:
            return False
        
        if not self._evdev_device_path:
            self._evdev_device_path = self._find_keyboard_device()
        
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
                    log.warning(f"[KEYBOARD] pynput 启动失败：{e}，尝试 evdev")
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
        if platform.system() == 'Linux' and not platform.system() == 'Darwin':
            if not os.environ.get('DISPLAY'):
                if EVDEV_AVAILABLE:
                    self._use_evdev = True
                    self._evdev_device_path = self._find_keyboard_device()
                    if not self._evdev_device_path:
                        log.warning("[KEYBOARD] 无桌面环境且未找到键盘设备，键盘监听可能不可用")
                else:
                    log.warning("[KEYBOARD] 无桌面环境且 evdev 不可用，请安装 python-evdev")
        
        self.is_running = True
        listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        listener_thread.start()
        
        mode = "evdev" if self._use_evdev else "pynput"
        log.info(f"[KEYBOARD] 键盘监听服务已启动（模式：{mode}）")
    
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
                    try:
                        self.listener.ungrab()  # pyright: ignore[reportAttributeAccessIssue]
                    except Exception:
                        pass
                elif not self._use_evdev:
                    # pynput listener
                    try:
                        self.listener.stop()  # pyright: ignore[reportAttributeAccessIssue]
                    except Exception:
                        pass
            except Exception as e:
                log.debug(f"[KEYBOARD] 停止监听器时出错（可忽略）: {e}")
        
        # 等待线程结束
        time.sleep(THREAD_JOIN_TIMEOUT)
        log.info("[KEYBOARD] 键盘监听服务已停止")
    
    def get_status(self) -> Dict:
        """获取设备状态"""
        return {
            "is_running": self.is_running,
            "platform": platform.system(),
            "pynput_available": PYNPUT_AVAILABLE,
            "evdev_available": EVDEV_AVAILABLE,
            "use_evdev": self._use_evdev
        }
