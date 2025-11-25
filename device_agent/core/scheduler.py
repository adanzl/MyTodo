"""
定时任务调度器模块
使用 APScheduler 实现 cron 定时任务
"""
import subprocess
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from core.config import get_config
from core.log_config import root_logger

log = root_logger()

# 延迟导入以避免循环依赖
_playlist_player = None

def get_playlist_player():
    """获取播放列表播放器模块（延迟导入）"""
    global _playlist_player
    if _playlist_player is None:
        from core.playlist_player import play_next_track
        _playlist_player = play_next_track
    return _playlist_player


class CronScheduler:
    """定时任务调度器"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
        self.config = get_config()
        self.job_id = 'cron_command_job'
        self._started = False  # 标记是否已经调用过 start()
        self._executing = False  # 标记是否正在执行任务
        self._execute_lock = threading.Lock()  # 执行锁
    
    def execute_command(self):
        """执行配置的命令（带执行锁保护）"""
        # 尝试获取执行锁，如果获取失败说明上一次还在执行
        if not self._execute_lock.acquire(blocking=False):
            log.warning("定时任务正在执行中，跳过本次触发")
            return
        
        try:
            self._executing = True
            command = self.config.get_cron_command()
            
            if not command:
                log.warning("未配置 cron.command，跳过执行")
                return
            
            log.info(f"执行定时任务命令: {command}")
            
            # 检查是否是播放列表播放命令
            if command.strip() == "play_next_track":
                log.info("检测到播放列表播放命令，调用播放器...")
                play_next_track_func = get_playlist_player()
                success = play_next_track_func()
                if success:
                    log.info("播放列表播放成功")
                else:
                    log.warning("播放列表播放失败")
                return
            
            # 执行普通 shell 命令
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                log.info(f"命令执行成功: {command}")
                if result.stdout:
                    log.info(f"输出: {result.stdout}")
            else:
                log.error(f"命令执行失败: {command}, 返回码: {result.returncode}")
                if result.stderr:
                    log.error(f"错误输出: {result.stderr}")
                    
        except subprocess.TimeoutExpired:
            log.error(f"命令执行超时: {command}")
        except Exception as e:
            log.error(f"命令执行异常: {command}, 错误: {str(e)}")
        finally:
            # 执行完成，释放锁
            self._executing = False
            self._execute_lock.release()
            log.debug("定时任务执行完成，释放执行锁")
    
    def parse_cron_expression(self, cron_expr: str) -> dict:
        """
        解析 cron 表达式为 APScheduler 参数
        支持标准 cron 格式: 分 时 日 月 周
        例如: "0 2 * * *" 表示每天凌晨2点执行
        """
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            raise ValueError(f"无效的 cron 表达式: {cron_expr}，应为 5 个字段（分 时 日 月 周）")
        
        minute, hour, day, month, day_of_week = parts
        
        return {
            'minute': minute,
            'hour': hour,
            'day': day,
            'month': month,
            'day_of_week': day_of_week
        }
    
    def start(self):
        """启动调度器"""
        log.debug(f"[DEBUG] start() 被调用，当前 _started={self._started}, id={id(self)}")
        
        # 检查是否已经调用过 start()，避免重复初始化
        if self._started:
            log.info(f"定时任务调度器已经初始化过，跳过重复调用 (实例ID: {id(self)})")
            return
        
        # 标记为已启动
        self._started = True
        log.debug(f"[DEBUG] 设置 _started=True, id={id(self)}")
        
        if not self.config.is_cron_enabled():
            log.info("定时任务未启用 (cron.enabled=false)")
            return
        
        cron_expr = self.config.get_cron_expression()
        command = self.config.get_cron_command()
        
        if not cron_expr:
            log.warning("未配置 cron.expression，无法启动定时任务")
            return
        
        if not command:
            log.warning("未配置 cron.command，无法启动定时任务")
            return
        
        try:
            # 解析 cron 表达式
            cron_params = self.parse_cron_expression(cron_expr)
            
            # 创建 cron 触发器
            trigger = CronTrigger(**cron_params, timezone='Asia/Shanghai')
            
            # 添加任务（max_instances=1 确保同时只有一个实例在执行）
            self.scheduler.add_job(
                self.execute_command,
                trigger=trigger,
                id=self.job_id,
                name='定时执行命令',
                replace_existing=True,
                max_instances=1  # 同时只允许一个实例执行
            )
            
            # 启动调度器
            self.scheduler.start()
            log.info(f"定时任务已启动: cron={cron_expr}, command={command}")
            
        except Exception as e:
            log.error(f"启动定时任务失败: {str(e)}")
    
    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            log.info("定时任务调度器已停止")
    
    def restart(self):
        """重启调度器"""
        try:
            # 重新加载配置
            self.config.reload()
            
            # 如果调度器正在运行，先移除旧任务
            if self.scheduler.running:
                try:
                    self.scheduler.remove_job(self.job_id)
                    log.info("已移除旧的定时任务")
                except Exception:
                    pass
            else:
                # 如果调度器未运行，启动它
                self.scheduler.start()
            
            # 如果未启用，停止调度器
            if not self.config.is_cron_enabled():
                if self.scheduler.running:
                    self.scheduler.shutdown()
                log.info("定时任务未启用，已停止调度器")
                return
            
            # 获取新配置
            cron_expr = self.config.get_cron_expression()
            command = self.config.get_cron_command()
            
            if not cron_expr or not command:
                log.warning("Cron 配置不完整，无法重启定时任务")
                return
            
            # 解析 cron 表达式并添加新任务
            cron_params = self.parse_cron_expression(cron_expr)
            trigger = CronTrigger(**cron_params, timezone='Asia/Shanghai')
            
            self.scheduler.add_job(
                self.execute_command,
                trigger=trigger,
                id=self.job_id,
                name='定时执行命令',
                replace_existing=True,
                max_instances=1  # 同时只允许一个实例执行
            )
            
            log.info(f"定时任务已重启: cron={cron_expr}, command={command}")
            
        except Exception as e:
            log.error(f"重启定时任务失败: {str(e)}")
            raise
    
    def is_executing(self) -> bool:
        """检查是否正在执行任务"""
        return self._executing
    
    def get_status(self) -> dict:
        """获取调度器状态"""
        return {
            'running': self.scheduler.running if self.scheduler else False,
            'enabled': self.config.is_cron_enabled(),
            'cron_expression': self.config.get_cron_expression(),
            'command': self.config.get_cron_command(),
            'is_executing': self._executing,
            'jobs': [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in self.scheduler.get_jobs()
            ] if self.scheduler.running else []
        }


# 全局调度器实例
_scheduler_instance = None
_scheduler_lock = threading.Lock()


def get_scheduler() -> CronScheduler:
    """获取全局调度器实例（线程安全单例）"""
    global _scheduler_instance
    
    # 双重检查锁定模式
    if _scheduler_instance is None:
        with _scheduler_lock:
            if _scheduler_instance is None:
                import os
                _scheduler_instance = CronScheduler()
                log.info(f"创建定时任务调度器实例 (PID: {os.getpid()}, 实例ID: {id(_scheduler_instance)})")
    
    return _scheduler_instance

