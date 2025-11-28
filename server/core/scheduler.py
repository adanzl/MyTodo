"""
定时任务调度器
负责管理和执行后台 cron 定时任务
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from datetime import datetime
from typing import Callable, Optional
from core.log_config import root_logger

log = root_logger()

# 设置 APScheduler 的日志级别为 WARNING，减少任务执行的 INFO 日志
logging.getLogger('apscheduler').setLevel(logging.WARNING)


class TaskScheduler:
    """
    定时任务调度器类
    支持 cron 表达式、间隔执行、定时执行等多种任务调度方式
    """

    _instance = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(TaskScheduler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化调度器"""
        if self._initialized:
            return

        self.scheduler = BackgroundScheduler(
            timezone='Asia/Shanghai',  # 设置时区
            job_defaults={
                'coalesce': True,  # 合并错过的任务
                'max_instances': 1  # 每个任务同时只允许一个实例
            })

        # 添加任务执行监听器
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

        self._initialized = True
        log.info("任务调度器初始化成功")

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            log.info("任务调度器已启动")
        else:
            log.warning("任务调度器已经在运行中")

    def shutdown(self, wait: bool = True):
        """
        关闭调度器
        :param wait: 是否等待所有任务执行完毕
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            log.info("任务调度器已关闭")

    def _convert_standard_cron_weekday_to_apscheduler(self, day_of_week: str) -> str:
        """
        将标准 cron 的周几映射转换为 APScheduler 的周几映射
        
        标准 cron: 0=周日, 1=周一, 2=周二, 3=周三, 4=周四, 5=周五, 6=周六
        APScheduler: 0=周一, 1=周二, 2=周三, 3=周四, 4=周五, 5=周六, 6=周日
        
        转换公式: (标准cron + 6) % 7
        
        :param day_of_week: 标准 cron 的周几字段（可能是 *、数字、范围、列表等）
        :return: 转换后的 APScheduler 周几字段
        """
        if day_of_week == '*':
            return '*'
        
        def convert_single_day(day_str: str) -> str:
            """转换单个周几数字"""
            try:
                day_num = int(day_str)
                # 转换公式: (标准cron + 6) % 7
                apscheduler_day = (day_num + 6) % 7
                return str(apscheduler_day)
            except ValueError:
                # 如果不是数字，可能是字符串别名或其他格式，直接返回
                return day_str
        
        # 处理范围表达式，如 "1-5"
        if '-' in day_of_week:
            parts = day_of_week.split('-')
            if len(parts) == 2:
                start = convert_single_day(parts[0])
                end = convert_single_day(parts[1])
                return f"{start}-{end}"
        
        # 处理列表表达式，如 "1,3,5" 或 "*/2"
        if ',' in day_of_week:
            days = day_of_week.split(',')
            converted_days = [convert_single_day(day.strip()) for day in days]
            return ','.join(converted_days)
        
        # 处理步进表达式，如 "*/2" 或 "1-5/2"
        if '/' in day_of_week:
            parts = day_of_week.split('/')
            if len(parts) == 2:
                base = parts[0]
                step = parts[1]
                converted_base = self._convert_standard_cron_weekday_to_apscheduler(base)
                return f"{converted_base}/{step}"
        
        # 单个数字
        return convert_single_day(day_of_week)

    def add_cron_job(self, func: Callable, job_id: str, cron_expression: Optional[str] = None, **cron_kwargs):
        """
        添加 cron 定时任务
        
        :param func: 要执行的函数
        :param job_id: 任务唯一标识
        :param cron_expression: cron 表达式 (如果提供，会覆盖 cron_kwargs)
        :param cron_kwargs: cron 参数
            - second: 秒 (0-59)
            - minute: 分钟 (0-59)
            - hour: 小时 (0-23)
            - day: 日 (1-31)
            - month: 月 (1-12)
            - day_of_week: 星期几 (0-6 或 mon,tue,wed,thu,fri,sat,sun)
        
        示例:
            # 每天早上 8 点执行
            scheduler.add_cron_job(my_func, 'daily_task', hour=8, minute=0)
            
            # 每周一到周五上午 9 点执行
            scheduler.add_cron_job(my_func, 'weekday_task', 
                                   day_of_week='mon-fri', hour=9, minute=0)
            
            # 每 5 分钟执行一次
            scheduler.add_cron_job(my_func, 'interval_task', minute='*/5')
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
                    converted_day_of_week = self._convert_standard_cron_weekday_to_apscheduler(day_of_week)
                    trigger = CronTrigger(
                        second=second,
                        minute=minute,
                        hour=hour,
                        day=day,
                        month=month,
                        day_of_week=converted_day_of_week
                    )
                elif len(parts) == 5:
                    # 5 字段格式：分 时 日 月 周（标准 cron）
                    # 手动解析并转换，不使用 from_crontab()（因为它有 bug）
                    minute, hour, day, month, day_of_week = parts
                    # 转换标准 cron 周几到 APScheduler 周几
                    converted_day_of_week = self._convert_standard_cron_weekday_to_apscheduler(day_of_week)
                    trigger = CronTrigger(
                        minute=minute,
                        hour=hour,
                        day=day,
                        month=month,
                        day_of_week=converted_day_of_week
                    )
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
                         func: Callable,
                         job_id: str,
                         seconds: int = 0,
                         minutes: int = 0,
                         hours: int = 0,
                         days: int = 0,
                         start_date: Optional[datetime] = None):
        """
        添加间隔执行任务
        
        :param func: 要执行的函数
        :param job_id: 任务唯一标识
        :param seconds: 间隔秒数
        :param minutes: 间隔分钟数
        :param hours: 间隔小时数
        :param days: 间隔天数
        :param start_date: 开始时间
        
        示例:
            # 每 30 秒执行一次
            scheduler.add_interval_job(my_func, 'interval_30s', seconds=30)
            
            # 每 2 小时执行一次
            scheduler.add_interval_job(my_func, 'interval_2h', hours=2)
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

    def add_date_job(self, func: Callable, job_id: str, run_date: datetime):
        """
        添加定时执行任务（只执行一次）
        
        :param func: 要执行的函数
        :param job_id: 任务唯一标识
        :param run_date: 执行时间
        
        示例:
            from datetime import datetime, timedelta
            # 1小时后执行
            run_time = datetime.now() + timedelta(hours=1)
            scheduler.add_date_job(my_func, 'once_task', run_time)
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

    def remove_job(self, job_id: str):
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

    def pause_job(self, job_id: str):
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

    def resume_job(self, job_id: str):
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

    def get_job(self, job_id: str):
        """
        获取任务信息
        :param job_id: 任务唯一标识
        :return: Job 对象或 None
        """
        return self.scheduler.get_job(job_id)

    def get_all_jobs(self):
        """
        获取所有任务列表
        :return: Job 对象列表
        """
        return self.scheduler.get_jobs()

    def print_jobs(self):
        """打印所有任务信息"""
        jobs = self.get_all_jobs()
        if not jobs:
            log.info("当前没有任何定时任务")
            return

        log.info(f"当前共有 {len(jobs)} 个定时任务:")
        for job in jobs:
            log.info(f"  - ID: {job.id}, 名称: {job.name}, 下次执行时间: {job.next_run_time}")

    def _job_executed_listener(self, event):
        """
        任务执行监听器
        :param event: 事件对象
        """
        if event.exception:
            log.error(f"任务执行失败: {event.job_id}, 异常: {event.exception}")


# 全局调度器实例
_scheduler_instance = None


def get_scheduler() -> TaskScheduler:
    """
    获取全局调度器实例
    :return: TaskScheduler 实例
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance


def init_scheduler():
    """初始化并启动调度器"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


# 示例任务函数
def example_task():
    """示例任务"""
    log.info(f"执行示例任务: {datetime.now()}")


if __name__ == '__main__':
    # 测试代码
    scheduler = TaskScheduler()

    # 添加每 10 秒执行一次的任务
    scheduler.add_interval_job(example_task, 'test_interval', seconds=10)

    # 添加每分钟执行一次的 cron 任务
    scheduler.add_cron_job(example_task, 'test_cron', minute='*/1')

    # 启动调度器
    scheduler.start()

    # 打印所有任务
    scheduler.print_jobs()

    # 保持运行
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()
        log.info("调度器已停止")
