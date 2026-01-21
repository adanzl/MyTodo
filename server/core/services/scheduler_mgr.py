"""
定时任务调度器
负责管理和执行后台 cron 定时任务
"""
import logging
from apscheduler.schedulers.gevent import GeventScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.executors.gevent import GeventExecutor
from datetime import datetime
from typing import Callable, Optional, Any, List
from core.config import app_logger
from core.utils import convert_standard_cron_weekday_to_apscheduler

log = app_logger

# 设置 APScheduler 的日志级别为 WARNING，减少任务执行的 INFO 日志
logging.getLogger('apscheduler').setLevel(logging.WARNING)


class SchedulerMgr:
    """
    定时任务调度器类
    支持 cron 表达式、间隔执行、定时执行等多种任务调度方式
    """

    _instance = None

    def __new__(cls) -> "SchedulerMgr":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(SchedulerMgr, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """初始化调度器"""
        if self._initialized:
            return

        # 在 gevent 环境中使用 GeventScheduler 和 GeventExecutor
        # 这样可以避免与 gevent hub 的冲突，确保定时任务能够正常执行和退出
        executor = GeventExecutor()

        self.scheduler = GeventScheduler(
            timezone='Asia/Shanghai',  # 设置时区
            executors={'default': executor},
            job_defaults={
                'coalesce': True,  # 合并错过的任务
                'max_instances': 1  # 每个任务同时只允许一个实例
            })

        # 添加任务执行监听器
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

        self._initialized = True
        log.info("任务调度器初始化成功 (使用 GeventScheduler)")

    def start(self) -> None:
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            log.info("任务调度器已启动")
        else:
            log.warning("任务调度器已经在运行中")

    def shutdown(self, wait: bool = True) -> None:
        """关闭调度器。

        Args:
            wait (bool): 是否等待所有正在执行的任务完成后再关闭。
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            log.info("任务调度器已关闭")

    def add_cron_job(self,
                     func: Callable[..., Any],
                     job_id: str,
                     cron_expression: Optional[str] = None,
                     **cron_kwargs: Any) -> bool:
        """添加 cron 定时任务。

        支持两种方式：
        1) 传入 `cron_expression`（5 或 6 字段）；
        2) 传入 APScheduler 的 `CronTrigger` 参数（`cron_kwargs`）。

        Args:
            func (Callable[..., Any]): 要执行的函数。
            job_id (str): 任务唯一标识。
            cron_expression (Optional[str]): cron 表达式（如果提供，会覆盖 `cron_kwargs`）。
            **cron_kwargs (Any): APScheduler `CronTrigger` 参数，例如 `minute='*/5'`。

        Returns:
            bool: 是否添加成功。
        """
        try:
            # 如果任务已存在，先移除
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                log.info(f"移除已存在的任务: {job_id}")

            if cron_expression:
                # 解析 cron 表达式
                parts = cron_expression.strip().split()

                # 检查字段数量
                if len(parts) == 6:
                    # 6 字段格式：秒 分 时 日 月 周
                    second, minute, hour, day, month, day_of_week = parts
                    # 转换标准 cron 周几到 APScheduler 周几
                    converted_day_of_week = convert_standard_cron_weekday_to_apscheduler(day_of_week)
                    trigger = CronTrigger(second=second,
                                          minute=minute,
                                          hour=hour,
                                          day=day,
                                          month=month,
                                          day_of_week=converted_day_of_week)
                elif len(parts) == 5:
                    # 5 字段格式：分 时 日 月 周（标准 cron）
                    # 手动解析并转换，不使用 from_crontab()（因为它有 bug）
                    minute, hour, day, month, day_of_week = parts
                    # 转换标准 cron 周几到 APScheduler 周几
                    converted_day_of_week = convert_standard_cron_weekday_to_apscheduler(day_of_week)
                    trigger = CronTrigger(minute=minute,
                                          hour=hour,
                                          day=day,
                                          month=month,
                                          day_of_week=converted_day_of_week)
                else:
                    raise ValueError(f"不支持的 cron 表达式格式，字段数量: {len(parts)}，期望 5 或 6 个字段")
            else:
                trigger = CronTrigger(**cron_kwargs)

            self.scheduler.add_job(func, trigger=trigger, id=job_id, name=job_id, replace_existing=True)
            log.info(f"添加 cron 任务成功: {job_id}")
            return True
        except Exception as e:
            log.error(f"添加 cron 任务失败: {job_id}, 错误: {e}")
            return False

    def add_interval_job(self,
                         func: Callable[..., Any],
                         job_id: str,
                         seconds: int = 0,
                         minutes: int = 0,
                         hours: int = 0,
                         days: int = 0,
                         start_date: Optional[datetime] = None) -> bool:
        """添加间隔执行任务。

        Args:
            func (Callable[..., Any]): 要执行的函数。
            job_id (str): 任务唯一标识。
            seconds (int): 间隔秒数。
            minutes (int): 间隔分钟数。
            hours (int): 间隔小时数。
            days (int): 间隔天数。
            start_date (Optional[datetime]): 开始时间。

        Returns:
            bool: 是否添加成功。
        """
        try:
            # 如果任务已存在，先移除
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                log.info(f"移除已存在的任务: {job_id}")

            trigger = IntervalTrigger(seconds=seconds, minutes=minutes, hours=hours, days=days, start_date=start_date)

            self.scheduler.add_job(func, trigger=trigger, id=job_id, name=job_id, replace_existing=True)
            log.info(f"添加间隔任务成功: {job_id}, 间隔: {days}天 {hours}时 {minutes}分 {seconds}秒")
            return True
        except Exception as e:
            log.error(f"添加间隔任务失败: {job_id}, 错误: {e}")
            return False

    def add_date_job(self, func: Callable[..., Any], job_id: str, run_date: datetime) -> bool:
        """添加定时执行任务（只执行一次）。

        Args:
            func (Callable[..., Any]): 要执行的函数。
            job_id (str): 任务唯一标识。
            run_date (datetime): 执行时间。

        Returns:
            bool: 是否添加成功。
        """
        try:
            # 如果任务已存在，先移除
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                log.info(f"移除已存在的任务: {job_id}")

            trigger = DateTrigger(run_date=run_date)

            self.scheduler.add_job(func, trigger=trigger, id=job_id, name=job_id, replace_existing=True)
            log.info(f"添加定时任务成功: {job_id}, 执行时间: {run_date}")
            return True
        except Exception as e:
            log.error(f"添加定时任务失败: {job_id}, 错误: {e}")
            return False

    def remove_job(self, job_id: str) -> bool:
        """
        移除任务
        :param job_id: 任务唯一标识
        """
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                log.info(f"移除任务成功: {job_id}")
                return True
            else:
                log.warning(f"任务不存在: {job_id}")
                return False
        except Exception as e:
            log.error(f"移除任务失败: {job_id}, 错误: {e}")
            return False

    def pause_job(self, job_id: str) -> bool:
        """
        暂停任务
        :param job_id: 任务唯一标识
        """
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.pause_job(job_id)
                log.info(f"暂停任务成功: {job_id}")
                return True
            else:
                log.warning(f"任务不存在: {job_id}")
                return False
        except Exception as e:
            log.error(f"暂停任务失败: {job_id}, 错误: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """
        恢复任务
        :param job_id: 任务唯一标识
        """
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.resume_job(job_id)
                log.info(f"恢复任务成功: {job_id}")
                return True
            else:
                log.warning(f"任务不存在: {job_id}")
                return False
        except Exception as e:
            log.error(f"恢复任务失败: {job_id}, 错误: {e}")
            return False

    def get_job(self, job_id: str) -> Any:
        """
        获取任务信息
        :param job_id: 任务唯一标识
        :return: Job 对象或 None
        """
        return self.scheduler.get_job(job_id)

    def get_all_jobs(self) -> List[Any]:
        """
        获取所有任务列表
        :return: Job 对象列表
        """
        return self.scheduler.get_jobs()

    def print_jobs(self) -> None:
        """打印所有任务信息"""
        jobs = self.get_all_jobs()
        if not jobs:
            log.info("当前没有任何定时任务")
            return

        log.info(f"当前共有 {len(jobs)} 个定时任务:")
        for job in jobs:
            log.info(f"  - ID: {job.id}, 名称: {job.name}, 下次执行时间: {job.next_run_time}")

    def _job_executed_listener(self, event: Any) -> None:
        """
        任务执行监听器
        :param event: 事件对象
        """
        if event.exception:
            # 捕获 gevent 相关的异常，避免影响线程池 worker
            import gevent
            if isinstance(event.exception, gevent.exceptions.LoopExit):
                log.warning(f"任务执行后发生 gevent LoopExit (可忽略): {event.job_id}, 异常: {event.exception}")
            else:
                log.error(f"任务执行失败: {event.job_id}, 异常: {event.exception}")


# 全局调度器实例
scheduler_mgr = SchedulerMgr()


# 示例任务函数
def example_task():
    """示例任务"""
    log.info(f"执行示例任务: {datetime.now()}")


if __name__ == '__main__':
    # 测试代码

    # 添加每 10 秒执行一次的任务
    scheduler_mgr.add_interval_job(example_task, 'test_interval', seconds=10)

    # 添加每分钟执行一次的 cron 任务
    scheduler_mgr.add_cron_job(example_task, 'test_cron', minute='*/1')

    # 启动调度器
    scheduler_mgr.start()

    # 打印所有任务
    scheduler_mgr.print_jobs()

    # 保持运行
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler_mgr.shutdown()
        log.info("调度器已停止")
