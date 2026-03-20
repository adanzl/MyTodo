'''
键盘监听服务
监听所有按键并输出日志，F12~F19 按键可配置发送 HTTP 请求
'''
import json
import os
import platform
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Tuple, Union

from core.log_config import root_logger
from core.config import config_mgr
from core.utils import _send_http_request
from core.device.keyboard_dev import KeyboardDev, KEY_NAMES

log = root_logger()

# ==================== 常量定义 ====================
# F12~F19 按键名列表（从 keyboard_dev 导入）

# 向后兼容：KEY_CODES 字典（用于 API 验证）
KEY_CODES = {name: name for name in KEY_NAMES}

# 配置键后缀
CONFIG_SUFFIXES = ["url", "method", "data"]

# 默认 HTTP 方法
DEFAULT_HTTP_METHOD = "GET"

# 默认 F12 URL
DEFAULT_F12_URL = "http://localhost:8000/keyboard/status"




class KeyboardMgr:
    """键盘监听管理器 - 负责按键逻辑和业务处理"""

    def __init__(self):
        log.info("[KEYBOARD] KeyboardMgr init")
        self.handlers: Dict[str, Callable] = {}  # 按键名 -> 处理函数
        self._lock = threading.Lock()
        self._base_url_cache: Optional[str] = None  # URL 构建缓存
        
        # 初始化硬件设备
        self._device = KeyboardDev()

    def set_handler(self, key: str, handler: Callable):
        """
        设置按键处理函数
        :param key: 按键名 (F12~F19)
        :param handler: 处理函数，接收按键名作为参数
        """
        if key not in KEY_NAMES:
            raise ValueError(f"不支持的按键：{key}，仅支持 F12~F19")

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

    def _on_key_press(self, key_name: str):
        """
        统一的按键回调（由 keyboard_dev 调用）
        :param key_name: 按键名称
        """
        self._trigger_handler(key_name)

    def _trigger_handler(self, key_name: str):
        """触发按键处理函数"""
        with self._lock:
            handler = self.handlers.get(key_name)

        if handler:
            try:
                handler(key_name)
            except Exception as e:
                log.error(f"[KEYBOARD] 处理按键 {key_name} 时出错：{e}")
        else:
            log.debug(f"[KEYBOARD] 按键 {key_name} 未设置处理函数")

    def start(self):
        """启动监听服务"""
        # 注册统一的按键回调到硬件设备
        self._device.set_on_press_handler(self._on_key_press)
        self._device.start()

    def stop(self):
        """停止监听服务"""
        self._device.stop()

    def get_status(self) -> Dict:
        """获取服务状态"""
        device_status = self._device.get_status()
        return {
            "is_running": device_status["is_running"],
            "handlers": list(self.handlers.keys()),
            "platform": device_status["platform"],
            "supported": True,
            "pynput_available": device_status["pynput_available"],
            "evdev_available": device_status["evdev_available"]
        }

    # ==================== 工具方法 ====================
    def _get_config_key(self, key_name: str, suffix: str) -> str:
        """构建配置键名"""
        return f"keyboard.{key_name}.{suffix}"

    def _get_base_url(self) -> Optional[str]:
        """获取并缓存 center_server_url 的基础 URL"""
        if self._base_url_cache is None:
            base_url = config_mgr.get('center_server_url', '')
            if base_url:
                # 移除末尾的斜杠
                self._base_url_cache = base_url.rstrip('/')
        return self._base_url_cache

    def _clear_base_url_cache(self):
        """清除 base_url 缓存（用于配置更新后）"""
        self._base_url_cache = None

    def _build_full_url(self, url: str) -> Optional[str]:
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
        base_url = self._get_base_url()
        if not base_url:
            log.warning(f"[KEYBOARD] center_server_url 未配置，无法构建完整 URL: {url}")
            return None

        # 确保 url 以 / 开头
        if not url.startswith('/'):
            url = '/' + url

        return f"{base_url}{url}"

    def _parse_config_data(self, data_str: str) -> Dict:
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
            log.warning(f"[KEYBOARD] 数据格式错误，忽略：{data_str}")
        return {}

    def _get_key_config_raw(self, key: str) -> Optional[Dict[str, Optional[str]]]:
        """
        获取按键的原始配置（不构建 URL）
        :param key: 按键名
        :return: 配置字典，包含 url, method, data，如果未配置则返回 None
        """
        url_config = config_mgr.get(self._get_config_key(key, "url"))
        if not url_config:
            return None

        return {
            "url": url_config,
            "method": config_mgr.get(self._get_config_key(key, "method"), DEFAULT_HTTP_METHOD),
            "data": config_mgr.get(self._get_config_key(key, "data"), "")
        }
    
    def _is_within_valid_time(self) -> Tuple[bool, str]:
        """
        检查当前时间是否在有效时间范围内
        :return: (is_valid: bool, reason: str)
        """
        valid_time_str = config_mgr.get("key_valid_time", "")
        duration_str = config_mgr.get("key_valid_duration", "")
        
        # 如果没有配置有效时间，则认为始终有效
        if not valid_time_str:
            return True, "未配置有效时间限制"
        
        # 解析开始时间（格式：HH:MM）
        valid_time_parts = valid_time_str.split(":")
        if len(valid_time_parts) != 2:
            log.warning(f"[KEYBOARD] 无效的时间格式：{valid_time_str}，应为 HH:MM")
            return True, "时间格式错误，跳过检查"
        
        try:
            start_hour = int(valid_time_parts[0])
            start_minute = int(valid_time_parts[1])
        except ValueError:
            log.warning(f"[KEYBOARD] 无效的时间值：{valid_time_str}")
            return True, "时间值解析失败，跳过检查"
        
        if not (0 <= start_hour <= 23 and 0 <= start_minute <= 59):
            log.warning(f"[KEYBOARD] 无效的时间值：{valid_time_str}")
            return True, "时间值超出范围，跳过检查"
        
        # 解析持续时间（分钟）
        duration_minutes = 0
        if duration_str:
            try:
                duration_minutes = int(duration_str)
                if duration_minutes < 0:
                    log.warning(f"[KEYBOARD] 无效的持续时间：{duration_str}")
                    duration_minutes = 0
            except ValueError:
                log.warning(f"[KEYBOARD] 无效的持续时间格式：{duration_str}")
                duration_minutes = 0
        
        # 获取当前时间
        now = datetime.now()
        
        # 构建开始时间（今天的 HH:MM）
        start_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        
        # 计算结束时间
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # 如果持续时间超过 24 小时，认为始终有效
        if duration_minutes >= 24 * 60:
            return True, f"持续时间超过 24 小时，始终有效"
        
        # 检查是否在时间范围内
        if start_time <= now <= end_time:
            return True, f"在有效时间内 ({start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')})"
        else:
            # 计算距离下次有效时间的剩余时间
            if now < start_time:
                next_valid = start_time
            else:
                # 已经过了今天的有效时间，计算明天的有效时间
                next_valid = start_time + timedelta(days=1)
            
            remaining = (next_valid - now).total_seconds()
            return False, f"不在有效时间内，下次有效时间：{next_valid.strftime('%Y-%m-%d %H:%M')}（约{int(remaining/60)}分钟后）"

    def _get_key_config(self, key: str) -> Optional[Dict]:
        """
        获取按键配置（构建完整 URL）
        :param key: 按键名
        :return: 配置字典，包含 method, url（完整 URL）, data，如果未配置或 URL 构建失败则返回 None
        """
        raw_config = self._get_key_config_raw(key)
        if not raw_config:
            return None
    
        # 构建完整 URL
        url_value = raw_config.get("url")
        if not url_value:
            return None
        full_url = self._build_full_url(url_value)
        if not full_url:
            return None
    
        result = {
            "method": raw_config.get("method", DEFAULT_HTTP_METHOD),
            "url": full_url,
        }
    
        # 解析数据
        data_value = raw_config.get("data")
        if data_value:
            data = self._parse_config_data(data_value)
            if data:
                result["data"] = data
    
        return result

    def _create_key_handler(self, key: str) -> Callable:
        """
        创建按键处理函数
        :param key: 按键名 (F13~F19)
        :return: 处理函数
        """
        def handler(key_name: str):
            # 首先检查时间有效性
            is_valid, reason = self._is_within_valid_time()
            if not is_valid:
                log.warning(f"[KEYBOARD] 按键 {key_name} 触发被阻止：{reason}")
                return
            
            config = self._get_key_config(key_name)
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
            result = _send_http_request(url, method=method, data=data, headers={})

            if not result.get("success"):
                log.error(f"[KEYBOARD] 按键 {key_name} 请求失败：{result.get('error')}")

        return handler

    def _setup_default_config(self):
        """设置 F12 的默认配置"""
        if not config_mgr.get(self._get_config_key("F12", "url")):
            config_mgr.set(self._get_config_key("F12", "url"), DEFAULT_F12_URL)
            config_mgr.set(self._get_config_key("F12", "method"), DEFAULT_HTTP_METHOD)
            config_mgr.save_config()
            log.info(f"[KEYBOARD] 已设置 F12 默认配置：{DEFAULT_HTTP_METHOD} {DEFAULT_F12_URL}")

    def get_keyboard_status(self) -> Dict:
        """
        获取键盘监听服务状态和配置
        :return: 状态字典
        """
        status = self.get_status()

        # 添加配置信息
        configs = {}
        for key in KEY_NAMES:
            key_config = self._get_key_config(key)
            if key_config:
                configs[key] = {
                    "method": key_config["method"],
                    "url": key_config["url"],
                    "data": key_config.get("data", {})
                }

        status["configs"] = configs
        return status

    def start_service(self) -> Tuple[bool, str]:
        """
        启动键盘监听服务
        :return: (success: bool, message: str)
        """
        try:
            log.info(f"===== [Start keyboard service] =====")
            # 设置所有已配置按键的处理函数
            # 设置 F12 的默认配置（如果未配置）
            self._setup_default_config()

            for key in KEY_NAMES:
                key_config = self._get_key_config(key)
                if key_config:
                    handler = self._create_key_handler(key)
                    self.set_handler(key, handler)
                    log.info(f"[KEYBOARD] 已配置按键 {key} -> {key_config['url']}")

            self.start()
            return True, "键盘监听服务已启动"
        except Exception as e:
            log.error(f"[KEYBOARD] 启动服务失败：{e}")
            return False, f"启动失败：{str(e)}"

    def stop_service(self) -> Tuple[bool, str]:
        """
        停止键盘监听服务
        :return: (success: bool, message: str)
        """
        try:
            self.stop()
            return True, "键盘监听服务已停止"
        except Exception as e:
            log.error(f"[KEYBOARD] 停止服务失败：{e}")
            return False, f"停止失败：{str(e)}"

    def _build_key_config(self, key: str) -> Dict[str, Union[str, dict, None]]:
        """
        构建单个按键配置
        :param key: 按键名
        :return: 配置字典
        """
        return self._get_key_config(key) or {}

    def get_key_config(self, key: Optional[str] = None) -> Dict[str, Union[str, dict, None]]:
        """
        获取按键配置
        :param key: 按键名，如果为 None 则返回所有按键配置
        :return: 配置字典
        """
        if key:
            # 返回单个按键配置
            if key not in KEY_NAMES:
                return {}
            return self._build_key_config(key)
        else:
            # 返回所有按键配置
            configs = {}
            for k in KEY_NAMES:
                key_config = self._build_key_config(k)
                if key_config:
                    configs[k] = key_config
            return configs

    def save_key_config(self, key: str, url: str, method: str, data: Optional[dict] = None) -> Tuple[bool, str, dict]:
        """
        保存按键配置
        :param key: 按键名
        :param url: 请求 URL
        :param method: HTTP 方法
        :param data: 请求数据
        :return: (success: bool, message: str, config_data: dict)
        """
        try:
            config_mgr.set(self._get_config_key(key, "url"), url)
            config_mgr.set(self._get_config_key(key, "method"), method)

            # 保存数据（如果有）
            if data:
                config_mgr.set(self._get_config_key(key, "data"), json.dumps(data))
            else:
                # 清除旧数据
                if config_mgr.get(self._get_config_key(key, "data")):
                    config_mgr.set(self._get_config_key(key, "data"), "")

            # 清除 URL 缓存（因为可能更新了 center_server_url）
            self._clear_base_url_cache()

            # 保存配置到文件
            if not config_mgr.save_config():
                return False, "保存配置失败", {}

            # 如果服务正在运行，更新处理函数
            if self._device.is_running:
                handler = self._create_key_handler(key)
                self.set_handler(key, handler)

            # 构建完整 URL 用于日志和返回
            full_url = self._build_full_url(url)
            if full_url:
                log.info(f"[KEYBOARD] 已配置按键 {key}: {method} {full_url}")
                return True, f"按键 {key} 配置已保存", {"method": method, "url": full_url, "data": data}
            else:
                log.warning(f"[KEYBOARD] 已保存按键 {key} 配置，但 URL 构建失败（请检查 center_server_url 配置）")
                return True, f"按键 {key} 配置已保存（URL: {url}）", {"method": method, "url": url, "data": data}
        except Exception as e:
            log.error(f"[KEYBOARD] 配置失败：{e}")
            return False, f"配置失败：{str(e)}", {}

    def delete_key_config(self, key: str) -> Tuple[bool, str]:
        """
        删除按键配置
        :param key: 按键名
        :return: (success: bool, message: str)
        """
        try:
            # 删除配置项
            for suffix in CONFIG_SUFFIXES:
                config_mgr.set(self._get_config_key(key, suffix), "")

            # 保存配置到文件
            if not config_mgr.save_config():
                return False, "保存配置失败"

            # 如果服务正在运行，移除处理函数
            if self._device.is_running:
                self.remove_handler(key)

            log.info(f"[KEYBOARD] 已删除按键 {key} 的配置")
            return True, f"按键 {key} 配置已删除"
        except Exception as e:
            log.error(f"[KEYBOARD] 删除配置失败：{e}")
            return False, f"删除失败：{str(e)}"

    def simulate_key_press(self, key: str) -> Tuple[bool, str, dict]:
        """
        模拟按键触发
        :param key: 按键名 (F13~F19)
        :return: (success: bool, message: str, result: dict)
        """
        try:
            if key not in KEY_NAMES:
                return False, f"不支持的按键：{key}，仅支持 {', '.join(KEY_NAMES)}", {}

            # 检查是否有配置该按键处理函数
            with self._lock:
                handler = self.handlers.get(key)

            if not handler:
                # 如果没有处理函数，尝试设置
                key_config = self._get_key_config(key)
                if not key_config:
                    return False, f"按键 {key} 未配置 URL 或 URL 构建失败（请检查 center_server_url 配置）", {}

                # 设置处理函数
                handler = self._create_key_handler(key)
                self.set_handler(key, handler)

            # 模拟按键触发
            log.info(f"[KEYBOARD] 模拟按键触发：{key}")
            try:
                handler(key)
                return True, f"按键 {key} 模拟触发成功", {}
            except Exception as e:
                log.error(f"[KEYBOARD] 模拟按键 {key} 触发失败：{e}")
                return False, f"触发失败：{str(e)}", {}

        except Exception as e:
            log.error(f"[KEYBOARD] 模拟按键失败：{e}")
            return False, f"模拟失败：{str(e)}", {}




# ==================== 全局实例 ====================
keyboard_mgr = KeyboardMgr()
