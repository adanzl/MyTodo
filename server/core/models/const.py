"""
目录常量管理
统一管理所有功能的目录路径
"""
import os

# 基础目录
BASE_TMP_DIR = '/tmp/my_todo'

# PDF 工具相关目录
PDF_BASE_DIR = os.path.join(BASE_TMP_DIR, 'pdf')
PDF_UPLOAD_DIR = os.path.join(PDF_BASE_DIR, 'upload')
PDF_UNLOCK_DIR = os.path.join(PDF_BASE_DIR, 'unlock')

# 媒体工具相关目录
MEDIA_BASE_DIR = os.path.join(BASE_TMP_DIR, 'media')
# 任务目录：/tmp/my_todo/media/{task_id}/
MEDIA_RESULT_DIR_SUFFIX = 'result'  # 结果目录后缀：{task_dir}/result/
FFMPEG_PATH = '/usr/bin/ffmpeg'  # ffmpeg 路径

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
