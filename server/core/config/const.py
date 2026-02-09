"""
目录常量管理
统一管理所有功能的目录路径

注意：BASE_TMP_DIR 用于保存真正的临时文件（处理过程中的中间文件）
      DEFAULT_BASE_DIR 用于保存项目文件、任务存档和生成的最终文件
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
load_dotenv()

# 临时文件基础目录（用于真正的临时文件，处理过程中的中间文件）
BASE_TMP_DIR = os.environ.get('BASE_TMP_DIR', '/tmp/my_todo')

# 项目文件基础目录（用于保存任务存档和生成的最终文件）
DEFAULT_BASE_DIR = os.environ.get('DEFAULT_BASE_DIR', 'data')

# PDF 工具相关目录（任务存档和最终文件保存在 base 目录）
PDF_BASE_DIR = os.path.join(DEFAULT_BASE_DIR, 'tasks', 'pdf')
PDF_UPLOAD_DIR = os.path.join(PDF_BASE_DIR, 'upload')
PDF_UNLOCK_DIR = os.path.join(PDF_BASE_DIR, 'unlock')

# 媒体工具相关目录（任务存档和最终文件保存在 base 目录）
MEDIA_BASE_DIR = os.path.join(DEFAULT_BASE_DIR, 'tasks', 'media')
# 任务目录：{DEFAULT_BASE_DIR}/tasks/media/{task_id}/
MEDIA_RESULT_DIR_SUFFIX = 'result'  # 结果目录后缀：{task_dir}/result/
# FFMPEG 工具配置（从环境变量读取，支持配置）
FFMPEG_PATH = os.environ.get('FFMPEG_PATH', '/usr/bin/ffmpeg')  # ffmpeg 路径
FFMPEG_TIMEOUT = int(os.environ.get('FFMPEG_TIMEOUT', '300'))  # ffmpeg 超时时间（秒）

# 媒体文件 MIME 映射
MIMETYPE_MAP = {
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.aac': 'audio/aac',
    '.ogg': 'audio/ogg',
    '.m4a': 'audio/mp4',
    '.mp4': 'video/mp4',
    '.avi': 'video/x-msvideo',
    '.mkv': 'video/x-matroska',
}


def get_media_task_dir(task_id: str) -> str:
    """获取媒体任务目录"""
    return os.path.join(MEDIA_BASE_DIR, task_id)


def get_media_task_result_dir(task_id: str) -> str:
    """获取媒体任务结果目录"""
    return os.path.join(get_media_task_dir(task_id), MEDIA_RESULT_DIR_SUFFIX)


# 允许的音频文件扩展名
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.wma'}

# 允许的 PDF 文件扩展名
ALLOWED_PDF_EXTENSIONS = {'.pdf'}

# 图片存储目录（DEFAULT_BASE_DIR 的 pic 子目录）
PIC_BASE_DIR = os.path.join(DEFAULT_BASE_DIR, 'pic')
# 允许的图片文件扩展名
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

# 任务状态常量（公共）
TASK_STATUS_PENDING = 'pending'  # 等待中
TASK_STATUS_PROCESSING = 'processing'  # 处理中
TASK_STATUS_SUCCESS = 'success'  # 成功
TASK_STATUS_FAILED = 'failed'  # 失败
TASK_STATUS_UPLOADED = 'uploaded'  # 已上传（PDF 工具专用）
