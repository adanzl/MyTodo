import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = "logs"
IS_PRODUCTION = os.environ.get('ENV', 'development').lower() == 'production'
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
    """
    配置根日志记录器
    
    :param IS_PRODUCTION: 是否为生产环境
    :return: 配置好的根日志记录器
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


def _create_access_logger() -> logging.Logger:
    """
    配置访问日志记录器
    
    :return: 配置好的访问日志记录器
    """
    access_logger = logging.getLogger('gevent.access')
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False  # 不传播到根日志记录器

    # 仅在生产环境创建访问日志文件，保留3天
    if IS_PRODUCTION:
        # 确保 logs 目录存在
        log_file = f"{LOG_DIR}/access.log"

        # 创建访问日志文件处理器（按天轮转，保留3天）
        access_handler = TimedRotatingFileHandler(log_file, when="midnight", backupCount=3, encoding="utf-8")

        # 配置访问日志格式：时间 方法 路径 状态码 响应时间 客户端IP User-Agent
        # gevent会自动添加请求信息到message中
        access_formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        access_handler.setFormatter(access_formatter)
        access_logger.addHandler(access_handler)
        # 确保日志级别正确
        access_logger.setLevel(logging.INFO)
        # 添加调试信息，确认 access_logger 已正确配置
        app_logger.info(
            f'Access logger configured: {access_logger.name}, handlers: {len(access_logger.handlers)}, propagate: {access_logger.propagate}, level: {access_logger.level}'
        )
    else:
        # 开发环境：创建一个空的日志记录器，不输出任何日志
        access_logger.setLevel(logging.CRITICAL)  # 设置为 CRITICAL 级别，几乎不记录任何日志

    return access_logger


access_logger = _create_access_logger()
