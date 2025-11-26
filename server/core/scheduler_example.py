"""
定时任务调度器使用示例
演示如何使用 TaskScheduler 类添加和管理定时任务
"""
from core.scheduler import get_scheduler
from core.log_config import root_logger
from datetime import datetime, timedelta

log = root_logger()


# ==================== 示例任务函数 ====================

def daily_report_task():
    """每日报表任务"""
    log.info("执行每日报表生成任务...")
    # 这里添加你的业务逻辑
    pass


def data_backup_task():
    """数据备份任务"""
    log.info("执行数据备份任务...")
    # 这里添加你的业务逻辑
    pass


def cleanup_task():
    """清理过期数据任务"""
    log.info("执行清理过期数据任务...")
    # 这里添加你的业务逻辑
    pass


def health_check_task():
    """健康检查任务"""
    log.info("执行系统健康检查...")
    # 这里添加你的业务逻辑
    pass


def send_notification_task():
    """发送通知任务"""
    log.info("发送用户通知...")
    # 这里添加你的业务逻辑
    pass


# ==================== 注册定时任务 ====================

def register_scheduled_tasks():
    """
    注册所有定时任务
    在应用启动时调用此函数来注册所有需要的定时任务
    """
    scheduler = get_scheduler()
    
    # 示例1: 每天早上 8 点执行日报任务
    scheduler.add_cron_job(
        daily_report_task,
        job_id='daily_report',
        hour=8,
        minute=0
    )
    
    # 示例2: 每天凌晨 2 点执行数据备份
    scheduler.add_cron_job(
        data_backup_task,
        job_id='data_backup',
        hour=2,
        minute=0
    )
    
    # 示例3: 每周日凌晨 3 点执行清理任务
    scheduler.add_cron_job(
        cleanup_task,
        job_id='weekly_cleanup',
        day_of_week='sun',
        hour=3,
        minute=0
    )
    
    # 示例4: 每 5 分钟执行一次健康检查
    scheduler.add_interval_job(
        health_check_task,
        job_id='health_check',
        minutes=5
    )
    
    # 示例5: 每小时的第 0 分和第 30 分执行（使用 cron 表达式）
    scheduler.add_cron_job(
        send_notification_task,
        job_id='half_hourly_notification',
        minute='0,30'
    )
    
    # 示例6: 使用标准 cron 表达式（每 15 分钟执行一次）
    scheduler.add_cron_job(
        health_check_task,
        job_id='cron_expression_example',
        cron_expression='*/15 * * * *'  # 分 时 日 月 周
    )
    
    # 示例7: 每工作日（周一到周五）上午 9 点执行
    scheduler.add_cron_job(
        daily_report_task,
        job_id='weekday_morning_task',
        day_of_week='mon-fri',
        hour=9,
        minute=0
    )
    
    # 示例8: 定时任务（1小时后执行一次）
    run_time = datetime.now() + timedelta(hours=1)
    scheduler.add_date_job(
        send_notification_task,
        job_id='one_time_task',
        run_date=run_time
    )
    
    log.info("所有定时任务已注册")
    scheduler.print_jobs()


# ==================== 任务管理示例 ====================

def manage_tasks_example():
    """演示如何管理任务"""
    scheduler = get_scheduler()
    
    # 暂停任务
    scheduler.pause_job('daily_report')
    
    # 恢复任务
    scheduler.resume_job('daily_report')
    
    # 移除任务
    scheduler.remove_job('one_time_task')
    
    # 获取任务信息
    job = scheduler.get_job('health_check')
    if job:
        log.info(f"任务信息: ID={job.id}, 下次执行={job.next_run_time}")
    
    # 获取所有任务
    all_jobs = scheduler.get_all_jobs()
    log.info(f"当前共有 {len(all_jobs)} 个任务")
    
    # 打印所有任务
    scheduler.print_jobs()


# ==================== 高级用法示例 ====================

def advanced_examples():
    """高级用法示例"""
    scheduler = get_scheduler()
    
    # 示例1: 每个月的第一天凌晨执行
    scheduler.add_cron_job(
        cleanup_task,
        job_id='monthly_task',
        day=1,
        hour=0,
        minute=0
    )
    
    # 示例2: 每年 1 月 1 日凌晨执行
    scheduler.add_cron_job(
        data_backup_task,
        job_id='yearly_task',
        month=1,
        day=1,
        hour=0,
        minute=0
    )
    
    # 示例3: 每 30 秒执行一次
    scheduler.add_interval_job(
        health_check_task,
        job_id='frequent_check',
        seconds=30
    )
    
    # 示例4: 每 2 小时执行一次
    scheduler.add_interval_job(
        data_backup_task,
        job_id='two_hourly_backup',
        hours=2
    )
    
    # 示例5: 指定开始时间的间隔任务
    start_time = datetime.now() + timedelta(minutes=10)
    scheduler.add_interval_job(
        send_notification_task,
        job_id='delayed_interval_task',
        minutes=30,
        start_date=start_time
    )


if __name__ == '__main__':
    # 注册所有定时任务
    register_scheduled_tasks()
    
    # 任务管理示例
    # manage_tasks_example()
    
    # 高级用法示例
    # advanced_examples()
