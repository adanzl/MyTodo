import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

from core.config import config

LOG_DIR = config.LOG_DIR
IS_PRODUCTION = config.IS_PRODUCTION
# 仅在 Linux 平台创建日志文件
if sys.platform == "linux":
    # 确保 logs 目录存在
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)


class HandlerFilter(logging.Filter):

    def filter(self, record):
        # 过滤 handler.py 的 INFO 级别日志（HTTP 请求日志）
        if record.filename == "handler.py" and record.levelno == logging.INFO:
            return False
        # 过滤 gevent.access 日志记录器的日志，避免写入 root_logger
        if record.name == "gevent.access":
            return False
        return True


handler_filter = HandlerFilter()


def _create_app_logger() -> logging.Logger:
    """配置根日志记录器。

    Returns:
        配置好的根日志记录器。
    """
    log_file = f"{LOG_DIR}/app.log"
    # cSpell: disable-next-line
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s')
    std_handler = logging.StreamHandler()
    std_handler.setFormatter(formatter)

    # 获取根日志记录器
    logger = logging.getLogger('app')
    logger.setLevel(logging.INFO)
    logger.addHandler(std_handler)

    for h in logger.handlers:
        h.addFilter(handler_filter)

    if IS_PRODUCTION:
        file_handler = TimedRotatingFileHandler(log_file, when="midnight", backupCount=3, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.addFilter(handler_filter)
        logger.addHandler(file_handler)
        logger.info(f'Root log: logs/app.log (rotating daily, keeping 3 days)')
    else:
        logger.info('Root log file: disabled (non-production environment)')
    return logger


app_logger = _create_app_logger()


def _create_access_logger() -> tuple[logging.Logger, logging.Logger]:
    """配置访问日志记录器。

    同时配置 'gevent.access' 和 'app.access' 两个记录器，使用相同的处理器，
    这样 gevent WSGIServer 和 Flask 中间件都能记录到同一个日志文件。
    仅在生产环境创建访问日志文件，开发环境不记录访问日志。

    Returns:
        (app_access_logger, gevent_access_logger) 配置好的访问日志记录器。
    """
    # 配置 gevent.access 记录器（供 gevent WSGIServer 使用）
    gevent_access_logger = logging.getLogger('gevent.access')
    gevent_access_logger.setLevel(logging.INFO)
    gevent_access_logger.propagate = False

    # 配置 app.access 记录器（供 Flask 中间件使用）
    app_access_logger = logging.getLogger('app.access')
    app_access_logger.setLevel(logging.INFO)
    app_access_logger.propagate = False

    # 仅在生产环境创建访问日志文件，保留3天
    if IS_PRODUCTION:
        log_file = f"{LOG_DIR}/access.log"

        # 创建访问日志文件处理器（按天轮转，保留3天）
        access_handler = TimedRotatingFileHandler(log_file, when="midnight", backupCount=3, encoding="utf-8")

        # 配置访问日志格式：时间 方法 路径 状态码 响应时间 客户端IP User-Agent
        access_formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        access_handler.setFormatter(access_formatter)

        # 为两个记录器添加处理器
        gevent_access_logger.addHandler(access_handler)
        app_access_logger.addHandler(access_handler)

        # 添加调试信息
        app_logger.info(
            f'Access logger configured: gevent.access and app.access, handlers: {len(app_access_logger.handlers)}, '
            f'propagate: {app_access_logger.propagate}, level: {app_access_logger.level}, log_file: {log_file}'
        )
        # 测试访问日志记录器是否能正常写入
        # gevent_access_logger.info('Gevent access logger test - if you see this, gevent logger is working')
        # app_access_logger.info('App access logger test - if you see this, app logger is working')
    else:
        # 开发环境：设置为 CRITICAL 级别，不记录任何日志
        gevent_access_logger.setLevel(logging.CRITICAL)
        app_access_logger.setLevel(logging.CRITICAL)
        app_logger.info('Access logger disabled (non-production environment)')

    return app_access_logger, gevent_access_logger


access_logger, gevent_access_logger = _create_access_logger()
