import logging
from logging.handlers import TimedRotatingFileHandler

# cSpell: disable-next-line
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = TimedRotatingFileHandler('logs/app.log', when="midnight", backupCount=3, encoding="utf-8")
std_handler = logging.StreamHandler()
std_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# 获取根日志记录器
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(std_handler)


def root_logger():
    return logger
