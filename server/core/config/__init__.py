"""
配置模块
统一管理配置、日志和常量
"""
from .config import Config, config
from .log_config import app_logger, access_logger, gevent_access_logger
from .const import (
    _SERVER_ROOT,
    BASE_TMP_DIR,
    DEFAULT_BASE_DIR,
    PDF_BASE_DIR,
    PDF_UPLOAD_DIR,
    PDF_UNLOCK_DIR,
    MEDIA_BASE_DIR,
    MEDIA_RESULT_DIR_SUFFIX,
    FFMPEG_PATH,
    FFMPEG_TIMEOUT,
    ALLOWED_AUDIO_EXTENSIONS,
    ALLOWED_PDF_EXTENSIONS,
    PIC_BASE_DIR,
    ALLOWED_IMAGE_EXTENSIONS,
    TASK_STATUS_PENDING,
    TASK_STATUS_PROCESSING,
    TASK_STATUS_SUCCESS,
    TASK_STATUS_FAILED,
    TASK_STATUS_UPLOADED,
    get_media_task_dir,
    get_media_task_result_dir,
    MIMETYPE_MAP,
)

__all__ = [
    # Config
    'Config',
    'config',
    # Loggers
    'app_logger',
    'access_logger',
    'gevent_access_logger',
    # Constants
    '_SERVER_ROOT',
    'BASE_TMP_DIR',
    'DEFAULT_BASE_DIR',
    'PDF_BASE_DIR',
    'PDF_UPLOAD_DIR',
    'PDF_UNLOCK_DIR',
    'MEDIA_BASE_DIR',
    'MEDIA_RESULT_DIR_SUFFIX',
    'FFMPEG_PATH',
    'FFMPEG_TIMEOUT',
    'ALLOWED_AUDIO_EXTENSIONS',
    'ALLOWED_PDF_EXTENSIONS',
    'PIC_BASE_DIR',
    'ALLOWED_IMAGE_EXTENSIONS',
    'TASK_STATUS_PENDING',
    'TASK_STATUS_PROCESSING',
    'TASK_STATUS_SUCCESS',
    'TASK_STATUS_FAILED',
    'TASK_STATUS_UPLOADED',
    # Functions
    'get_media_task_dir',
    'get_media_task_result_dir',
    'MIMETYPE_MAP',
]
