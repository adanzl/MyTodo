'''
心跳上报服务
每10秒向center服务器发送心跳，包含服务状态
'''
import socket
import threading
import time
import traceback
from typing import Dict, Optional, Tuple
from core.log_config import root_logger
from core.config import config_mgr
from core.utils import _send_http_request, get_local_ip
from core.service.keyboard import get_keyboard_status

log = root_logger()


class HeartbeatService:
    """心跳上报服务"""

    def __init__(self):
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.interval = 10  # 10秒间隔
        self._center_url: Optional[str] = None  # 缓存中心服务器地址
        self._port: Optional[int] = None  # 缓存端口
        self._name: Optional[str] = None  # 缓存名称

    def _get_center_url(self) -> Optional[str]:
        """获取center服务器地址（带缓存）"""
        if self._center_url is None:
            self._center_url = config_mgr.get('center_server_url', '').strip()
        return self._center_url

    def _get_port(self) -> int:
        """获取服务端口（带缓存）"""
        if self._port is None:
            port_str = config_mgr.get('server_port')
            if port_str:
                try:
                    self._port = int(port_str)
                except ValueError:
                    self._port = 8001
            else:
                self._port = 8001
        return self._port

    def _get_name(self) -> str:
        """获取服务名称，如果配置中没有则使用主机名（带缓存）"""
        if self._name is None:
            self._name = config_mgr.get('agent_name', socket.gethostname()).strip()
        return self._name

    def _collect_status(self) -> Dict:
        """
        收集服务状态
        :return: 状态字典
        """
        # 使用 try-except 避免获取状态时阻塞
        try:
            keyboard_status = get_keyboard_status()
        except Exception as e:
            log.debug(f"[HEARTBEAT] 获取键盘状态失败: {e}")
            keyboard_status = {"error": str(e)}

        ip = get_local_ip()
        port = self._get_port()
        address = f"http://{ip}:{port}"

        status = {
            "timestamp": int(time.time()),
            "address": address,
            "name": self._get_name(),
            "actions": ["bluetooth", "keyboard"],
            "keyboard": keyboard_status,
        }
        return status

    def _send_heartbeat(self) -> bool:
        """
        发送心跳
        :return: 是否发送成功
        """
        center_url = self._get_center_url()
        if not center_url:
            return False

        try:
            status = self._collect_status()
            result = _send_http_request(url=center_url,
                                        method="POST",
                                        data=status,
                                        headers={"Content-Type": "application/json"})

            if result.get("success"):
                log.debug(f"[HEARTBEAT] 心跳上报成功: {result.get('status_code')}")
                return True
            else:
                log.warning(f"[HEARTBEAT] 心跳上报失败: {result.get('error')}")
                return False
        except Exception as e:
            log.error(f"[HEARTBEAT] 心跳上报异常: {e}")
            return False

    def _heartbeat_loop(self):
        """心跳循环"""
        # 延迟第一次心跳，避免在应用启动时立即执行阻塞操作
        time.sleep(1)

        while self.is_running:
            try:
                self._send_heartbeat()
            except Exception as e:
                log.error(f"[HEARTBEAT] 心跳循环异常 Traceback: {traceback.format_exc()}")

            # 等待指定间隔时间，每秒检查一次运行状态
            for _ in range(self.interval):
                if not self.is_running:
                    break
                time.sleep(1)

        log.info("[HEARTBEAT] 心跳循环已退出")

    def start(self) -> bool:
        """
        启动心跳服务
        :return: 是否启动成功
        """
        if self.is_running:
            log.warning("[HEARTBEAT] 心跳服务已在运行")
            return False

        center_url = self._get_center_url()
        if not center_url:
            log.info("[HEARTBEAT] center_server_url 未配置，心跳服务不启动")
            return False

        # 先创建线程，再设置 is_running，确保线程启动时能正确读取状态
        self.is_running = True
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True, name="HeartbeatService")
        self.thread.start()
        log.info(f"[HEARTBEAT] 心跳服务已启动，上报地址: {center_url}，间隔: {self.interval}秒")
        return True

    def stop(self):
        """停止心跳服务"""
        if not self.is_running:
            return

        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        log.info("[HEARTBEAT] 心跳服务已停止")

    def get_status(self) -> Dict:
        """
        获取服务状态
        :return: 状态字典
        """
        return {"is_running": self.is_running, "interval": self.interval, "center_url": self._get_center_url()}


# 全局心跳服务实例
_heartbeat_service: Optional[HeartbeatService] = None


def get_heartbeat_service() -> HeartbeatService:
    """获取全局心跳服务实例"""
    global _heartbeat_service
    if _heartbeat_service is None:
        _heartbeat_service = HeartbeatService()
    return _heartbeat_service


def start_heartbeat_service() -> Tuple[bool, str]:
    """
    启动心跳服务
    :return: (success: bool, message: str)
    """
    try:
        service = get_heartbeat_service()
        log.info("[HEARTBEAT] 正在启动心跳服务...")
        center_url = service._get_center_url()

        success = service.start()
        if success:
            return True, f"心跳服务已启动，上报地址: {center_url}"
        else:
            log.warning("[HEARTBEAT] 心跳服务启动失败")
            return False, "心跳服务启动失败"
    except Exception as e:
        log.error(f"[HEARTBEAT] 启动服务失败 Traceback: {traceback.format_exc()}")
        return False, f"启动失败: {str(e)}"
