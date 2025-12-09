'''
心跳上报服务
每10秒向center服务器发送心跳，包含服务状态
'''
import threading
import time
from typing import Dict, Optional
from core.log_config import root_logger
from core.config import get_config
from core.utils import _send_http_request
from core.service.keyboard import get_keyboard_status

log = root_logger()


class HeartbeatService:
    """心跳上报服务"""
    
    def __init__(self):
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.interval = 10  # 10秒间隔
    
    def _get_center_url(self) -> Optional[str]:
        """获取center服务器地址"""
        config = get_config()
        return config.get('center_server_url')
    
    def _collect_status(self) -> Dict:
        """
        收集服务状态
        :return: 状态字典
        """
        status = {
            "timestamp": int(time.time()),
            "keyboard": get_keyboard_status(),
        }
        return status
    
    def _send_heartbeat(self):
        """发送心跳"""
        center_url = self._get_center_url()
        if not center_url:
            return
        
        try:
            status = self._collect_status()
            result = _send_http_request(
                url=f"{center_url}/heartbeat",
                method="POST",
                data=status,
                headers={"Content-Type": "application/json"}
            )
            
            if result.get("success"):
                log.debug(f"[HEARTBEAT] 心跳上报成功: {result.get('status_code')}")
            else:
                log.warning(f"[HEARTBEAT] 心跳上报失败: {result.get('error')}")
        except Exception as e:
            log.error(f"[HEARTBEAT] 心跳上报异常: {e}")
    
    def _heartbeat_loop(self):
        """心跳循环"""
        while self.is_running:
            try:
                self._send_heartbeat()
            except Exception as e:
                log.error(f"[HEARTBEAT] 心跳循环异常: {e}")
            
            # 等待10秒
            for _ in range(self.interval):
                if not self.is_running:
                    break
                time.sleep(1)
    
    def start(self):
        """启动心跳服务"""
        center_url = self._get_center_url()
        if not center_url:
            log.info("[HEARTBEAT] center_server_url 未配置，心跳服务不启动")
            return
        
        if self.is_running:
            log.warning("[HEARTBEAT] 心跳服务已在运行")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.thread.start()
        log.info(f"[HEARTBEAT] 心跳服务已启动，上报地址: {center_url}")
    
    def stop(self):
        """停止心跳服务"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        log.info("[HEARTBEAT] 心跳服务已停止")
    
    def get_status(self) -> Dict:
        """获取服务状态"""
        return {
            "is_running": self.is_running,
            "interval": self.interval,
            "center_url": self._get_center_url()
        }


# 全局心跳服务实例
_heartbeat_service: Optional[HeartbeatService] = None


def get_heartbeat_service() -> HeartbeatService:
    """获取全局心跳服务实例"""
    global _heartbeat_service
    if _heartbeat_service is None:
        _heartbeat_service = HeartbeatService()
    return _heartbeat_service


def start_heartbeat_service():
    """
    启动心跳服务
    :return: (success: bool, message: str)
    """
    try:
        service = get_heartbeat_service()
        service.start()
        if service.is_running:
            return True, "心跳服务已启动"
        else:
            return True, "心跳服务未启动（center_server_url 未配置）"
    except Exception as e:
        log.error(f"[HEARTBEAT] 启动服务失败: {e}")
        return False, f"启动失败: {str(e)}"


