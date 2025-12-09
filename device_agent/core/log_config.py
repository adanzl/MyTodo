import logging
import os
import platform
from logging.handlers import TimedRotatingFileHandler

# cSpell: disable-next-line
formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s')
std_handler = logging.StreamHandler()
std_handler.setFormatter(formatter)

# 获取根日志记录器
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 只在Linux平台添加文件处理器
if platform.system() == 'Linux':
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    file_handler = TimedRotatingFileHandler('logs/app.log', when="midnight", backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

logger.addHandler(std_handler)


class HandlerFilter(logging.Filter):

    def filter(self, record):
        # 只过滤 handler.py 相关日志
        return record.filename != "handler.py" or record.levelno > logging.INFO


for h in logger.handlers:
    h.addFilter(HandlerFilter())


def root_logger():
    return logger
