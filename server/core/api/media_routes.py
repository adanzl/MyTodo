'''
媒体管理路由
通过调用 device_agent 服务接口实现
'''
import os
import shutil
from datetime import datetime
from flask import Blueprint, request, send_file, abort
from werkzeug.utils import secure_filename

from core.log_config import app_logger
from core.services.audio_merge_mgr import audio_merge_mgr
from core.services.audio_convert_mgr import audio_convert_mgr
from core.models.const import get_media_task_dir, get_media_task_result_dir, ALLOWED_AUDIO_EXTENSIONS
from core.utils import get_media_url, get_media_duration, validate_and_normalize_path, _ok, _err, ensure_directory, is_allowed_audio_file, get_file_info, read_json_from_request, get_unique_filepath

log = app_logger
media_bp = Blueprint('media', __name__)

# 常量定义
DEFAULT_BASE_DIR = '/mnt'
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

# ========== 媒体文件服务接口（用于 DLNA 播放）==========


@media_bp.route("/media/getDuration", methods=['GET'])
def get_duration():
    """
    获取媒体文件的时长
    :return: 时长（秒）
    """
    try:
        file_path = request.args.get('path', '')

        # 验证和规范化路径
        normalized_path, error_msg = validate_and_normalize_path(file_path, DEFAULT_BASE_DIR, must_be_file=True)
        if error_msg:
            return _err(error_msg)

        # 获取媒体文件时长
        duration = get_media_duration(normalized_path)
        if duration is not None:
            return _ok({"duration": duration, "path": normalized_path})
        else:
            return _err("无法获取媒体文件时长")

    except PermissionError as e:
        file_path_str = file_path if 'file_path' in locals() else 'unknown'
        log.error(f"Permission denied for {file_path_str}: {e}")
        return _err(f"Permission denied: {str(e)}")
    except Exception as e:
        log.error(f"Error getting media duration: {e}")
        return _err(f"Error: {str(e)}")


@media_bp.route("/media/files/<path:filepath>", methods=['GET'])
def serve_media_file(filepath):
    """
    提供媒体文件访问服务（用于 DLNA 播放）
    :param filepath: 文件路径
    """
    try:
        # 安全处理：移除路径中的危险字符
        filepath = filepath.replace('../', '').replace('..\\', '')

        # 如果路径不是以 / 开头，添加 /
        if not filepath.startswith('/'):
            filepath = '/' + filepath

        # 检查文件是否存在
        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            log.warning(f"[MEDIA] File not found: {filepath}")
            abort(404)

        # 获取文件扩展名以确定 Content-Type
        ext = os.path.splitext(filepath)[1].lower()
        mimetype = MIMETYPE_MAP.get(ext, 'application/octet-stream')

        log.info(f"[MEDIA] Serving file: {filepath} (MIME: {mimetype})")
        return send_file(filepath, mimetype=mimetype)
    except Exception as e:
        log.error(f"[MEDIA] Error serving file {filepath}: {e}")
        abort(500)


# ========== 音频合成接口 ==========


@media_bp.route("/media/merge/create", methods=['POST'])
def create_media_task():
    """
    创建音频合成任务
    参数：
    - name: 任务名称
    """
    try:
        data = read_json_from_request()
        # 如果没有提供名称，使用当前日期时间作为默认名称
        name = data.get('name', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        code, msg, task_id = audio_merge_mgr.create_task(name)

        if code != 0:
            return _err(msg)

        task_info = audio_merge_mgr.get_task(task_id)
        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioMerge] 创建任务失败: {e}")
        return _err(f"创建任务失败: {str(e)}")


@media_bp.route("/media/merge/upload", methods=['POST'])
def upload_file():
    """
    上传文件到任务
    参数：
    - task_id: 任务ID（form 参数或查询参数）
    - file: 文件（multipart/form-data）
    """
    try:
        # 从 form 参数或查询参数获取 task_id
        task_id = request.form.get('task_id') or request.args.get('task_id')
        if not task_id:
            return _err("task_id 参数不能为空")

        if 'file' not in request.files:
            return _err("未找到上传的文件")

        file = request.files['file']
        if file.filename == '':
            return _err("文件名不能为空")

        if not is_allowed_audio_file(file.filename):
            return _err(f"不支持的文件类型，支持的格式: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}")

        # 确保任务目录存在
        task_dir = get_media_task_dir(task_id)
        ensure_directory(task_dir)

        # 保存文件，如果文件已存在则添加序号
        filename = secure_filename(file.filename)
        base_name, ext = os.path.splitext(filename)
        file_path = get_unique_filepath(task_dir, base_name, ext)
        filename = os.path.basename(file_path)

        file.save(file_path)
        log.info(f"[AudioMerge] 文件上传成功: {file_path}")

        # 添加到任务
        code, msg = audio_merge_mgr.add_file(task_id, file_path, filename)
        if code != 0:
            return _err(msg)

        file_info = get_file_info(file_path)
        return _ok(file_info)

    except Exception as e:
        log.error(f"[AudioMerge] 上传文件失败: {e}")
        return _err(f"上传文件失败: {str(e)}")


@media_bp.route("/media/merge/addFileByPath", methods=['POST'])
def add_file_by_path():
    """
    通过文件路径添加文件到任务
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    - file_path: 文件路径（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')
        file_path = data.get('file_path')

        if not task_id:
            return _err("task_id 参数不能为空")

        if not file_path:
            return _err("file_path 参数不能为空")

        # 验证文件路径
        normalized_path, error_msg = validate_and_normalize_path(file_path)
        if error_msg or not normalized_path:
            return _err(error_msg or "文件路径无效")
        file_path = normalized_path

        if not os.path.exists(file_path):
            return _err(f"文件不存在: {file_path}")

        if not os.path.isfile(file_path):
            return _err(f"路径不是文件: {file_path}")

        filename = os.path.basename(file_path)
        if not is_allowed_audio_file(filename):
            return _err(f"不支持的文件类型，支持的格式: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}")

        # 添加到任务
        code, msg = audio_merge_mgr.add_file(task_id, file_path, filename)
        if code != 0:
            return _err(msg)

        file_info = get_file_info(file_path)
        return _ok(file_info)

    except Exception as e:
        log.error(f"[AudioMerge] 添加文件失败: {e}")
        return _err(f"添加文件失败: {str(e)}")


@media_bp.route("/media/merge/deleteFile", methods=['POST'])
def delete_file():
    """
    从任务中删除文件
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    - file_index: 文件索引（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')
        file_index = data.get('file_index')

        if not task_id:
            return _err("task_id 参数不能为空")

        if file_index is None:
            return _err("file_index 参数不能为空")

        try:
            file_index = int(file_index)
        except (ValueError, TypeError):
            return _err("file_index 必须是整数")

        code, msg = audio_merge_mgr.remove_file(task_id, file_index)
        if code != 0:
            return _err(msg)

        return _ok({"message": msg})

    except Exception as e:
        log.error(f"[AudioMerge] 删除文件失败: {e}")
        return _err(f"删除文件失败: {str(e)}")


@media_bp.route("/media/merge/reorderFiles", methods=['POST'])
def reorder_files():
    """
    调整文件顺序
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    - file_indices: 新的文件索引顺序列表（JSON 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')
        file_indices = data.get('file_indices')

        if not task_id:
            return _err("task_id 参数不能为空")

        if not file_indices:
            return _err("file_indices 参数不能为空")

        if not isinstance(file_indices, list):
            return _err("file_indices 必须是数组")

        try:
            file_indices = [int(i) for i in file_indices]
        except (ValueError, TypeError):
            return _err("file_indices 必须都是整数")

        code, msg = audio_merge_mgr.reorder_files(task_id, file_indices)
        if code != 0:
            return _err(msg)

        task_info = audio_merge_mgr.get_task(task_id)
        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioMerge] 调整文件顺序失败: {e}")
        return _err(f"调整文件顺序失败: {str(e)}")


@media_bp.route("/media/merge/start", methods=['POST'])
def start_task():
    """
    开始音频合成任务
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')

        if not task_id:
            return _err("task_id 参数不能为空")

        code, msg = audio_merge_mgr.start_task(task_id)
        if code != 0:
            return _err(msg)

        task_info = audio_merge_mgr.get_task(task_id)
        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioMerge] 启动任务失败: {e}")
        return _err(f"启动任务失败: {str(e)}")


@media_bp.route("/media/merge/get", methods=['POST'])
def get_task_info():
    """
    获取任务信息
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')

        if not task_id:
            return _err("task_id 参数不能为空")

        task_info = audio_merge_mgr.get_task(task_id)
        if not task_info:
            return _err("任务不存在")

        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioMerge] 获取任务信息失败: {e}")
        return _err(f"获取任务信息失败: {str(e)}")


@media_bp.route("/media/merge/list", methods=['GET'])
def list_all_tasks():
    """
    列出所有任务
    """
    try:
        tasks = audio_merge_mgr.list_tasks()
        return _ok({"tasks": tasks})

    except Exception as e:
        log.error(f"[AudioMerge] 列出任务失败: {e}")
        return _err(f"列出任务失败: {str(e)}")


@media_bp.route("/media/merge/delete", methods=['POST'])
def delete_task():
    """
    删除任务
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')

        if not task_id:
            return _err("task_id 参数不能为空")

        code, msg = audio_merge_mgr.delete_task(task_id)
        if code != 0:
            return _err(msg)

        return _ok({"message": msg})

    except Exception as e:
        log.error(f"[AudioMerge] 删除任务失败: {e}")
        return _err(f"删除任务失败: {str(e)}")


@media_bp.route("/media/merge/download", methods=['GET'])
def download_result():
    """
    下载合成结果文件
    参数：
    - task_id: 任务ID（查询参数）
    """
    try:
        task_id = request.args.get('task_id')

        if not task_id:
            return _err("task_id 参数不能为空")

        task_info = audio_merge_mgr.get_task(task_id)
        if not task_info:
            return _err("任务不存在")

        if task_info['status'] != 'success' or not task_info.get('result_file'):
            return _err("任务未完成或结果文件不存在")

        result_file = task_info['result_file']
        if not os.path.exists(result_file):
            return _err("结果文件不存在")

        return send_file(result_file, as_attachment=True, download_name='merged.mp3')

    except Exception as e:
        log.error(f"[AudioMerge] 下载文件失败: {e}")
        return _err(f"下载文件失败: {str(e)}")


@media_bp.route("/media/merge/save", methods=['POST'])
def save_result():
    """
    转存合成结果文件到指定目录
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    - target_path: 目标目录路径（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')
        target_path = data.get('target_path')

        if not task_id:
            return _err("task_id 参数不能为空")

        if not target_path:
            return _err("target_path 参数不能为空")

        # 验证目标路径
        normalized_path, error_msg = validate_and_normalize_path(target_path, must_be_file=False)
        if error_msg or not normalized_path:
            return _err(error_msg or "目标路径无效")
        target_path = normalized_path

        if not os.path.exists(target_path):
            return _err(f"目标目录不存在: {target_path}")

        if not os.path.isdir(target_path):
            return _err(f"目标路径不是目录: {target_path}")

        # 获取任务信息
        task_info = audio_merge_mgr.get_task(task_id)
        if not task_info:
            return _err("任务不存在")

        if task_info['status'] != 'success' or not task_info.get('result_file'):
            return _err("任务未完成或结果文件不存在")

        result_file = task_info['result_file']
        if not os.path.exists(result_file):
            return _err("结果文件不存在")

        # 获取结果文件的扩展名，默认为 .mp3
        _, ext = os.path.splitext(result_file)
        ext = ext or '.mp3'

        # 生成唯一的目标文件路径：task_id + 扩展名，如果已存在则添加序号
        target_file = get_unique_filepath(target_path, task_id, ext)

        # 复制文件到目标目录
        shutil.copy2(result_file, target_file)
        log.info(f"[AudioMerge] 文件转存成功: {result_file} -> {target_file}")

        return _ok({"target_file": target_file, "message": "转存成功"})

    except Exception as e:
        log.error(f"[AudioMerge] 转存文件失败: {e}")
        return _err(f"转存文件失败: {str(e)}")


# ========== 音频转码接口 ==========


@media_bp.route("/media/convert/list", methods=['GET'])
def list_convert_tasks():
    """
    获取所有音频转码任务列表
    """
    try:
        tasks = audio_convert_mgr.get_task_list()
        return _ok({"tasks": tasks})
    except Exception as e:
        log.error(f"[AudioConvert] 列出任务失败: {e}")
        return _err(f"列出任务失败: {str(e)}")


@media_bp.route("/media/convert/create", methods=['POST'])
def create_convert_task():
    """
    创建音频转码任务
    参数：
    - name: 任务名称（可选）
    - output_dir: 输出目录名称（可选，默认为 'mp3'）
    - overwrite: 是否覆盖同名文件（可选，默认为 True）
    """
    try:
        data = read_json_from_request()
        # 如果没有提供名称，使用当前日期时间作为默认名称
        name = data.get('name', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        output_dir = data.get('output_dir')
        overwrite = data.get('overwrite')

        code, msg, task_id = audio_convert_mgr.create_task(name, output_dir=output_dir, overwrite=overwrite)

        if code != 0:
            return _err(msg)

        task_info = audio_convert_mgr.get_task(task_id)
        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioConvert] 创建任务失败: {e}")
        return _err(f"创建任务失败: {str(e)}")


@media_bp.route("/media/convert/get", methods=['POST'])
def get_convert_task_info():
    """
    获取音频转码任务详情
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')

        if not task_id:
            return _err("task_id 参数不能为空")

        task_info = audio_convert_mgr.get_task(task_id)
        if not task_info:
            return _err("任务不存在")

        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioConvert] 获取任务信息失败: {e}")
        return _err(f"获取任务信息失败: {str(e)}")


@media_bp.route("/media/convert/delete", methods=['POST'])
def delete_convert_task():
    """
    删除音频转码任务
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')

        if not task_id:
            return _err("task_id 参数不能为空")

        code, msg = audio_convert_mgr.delete_task(task_id)
        if code != 0:
            return _err(msg)

        return _ok({"success": True})

    except Exception as e:
        log.error(f"[AudioConvert] 删除任务失败: {e}")
        return _err(f"删除任务失败: {str(e)}")


@media_bp.route("/media/convert/update", methods=['POST'])
def update_convert_task():
    """
    更新音频转码任务信息
    参数：
    - task_id: 任务ID（JSON 或 form 参数，必填）
    - name: 任务名称（JSON 或 form 参数，可选）
    - directory: 目录路径（JSON 或 form 参数，可选）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')
        name = data.get('name')
        directory = data.get('directory')

        if not task_id:
            return _err("task_id 参数不能为空")

        # 至少需要提供一个要更新的字段
        output_dir = data.get('output_dir')
        overwrite = data.get('overwrite')
        if name is None and directory is None and output_dir is None and overwrite is None:
            return _err("至少需要提供一个要更新的字段（name、directory、output_dir 或 overwrite）")

        # 验证目录路径（如果提供了）
        if directory is not None:
            normalized_path, error_msg = validate_and_normalize_path(directory, must_be_file=False)
            if error_msg or not normalized_path:
                return _err(error_msg or "目录路径无效")
            directory = normalized_path

        code, msg = audio_convert_mgr.update_task(task_id,
                                                  name=name,
                                                  directory=directory,
                                                  output_dir=output_dir,
                                                  overwrite=overwrite)
        if code != 0:
            return _err(msg)

        task_info = audio_convert_mgr.get_task(task_id)
        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioConvert] 更新任务失败: {e}")
        return _err(f"更新任务失败: {str(e)}")


@media_bp.route("/media/convert/start", methods=['POST'])
def start_convert_task():
    """
    开始音频转码任务
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')

        if not task_id:
            return _err("task_id 参数不能为空")

        code, msg = audio_convert_mgr.start_task(task_id)
        if code != 0:
            return _err(msg)

        task_info = audio_convert_mgr.get_task(task_id)
        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioConvert] 启动任务失败: {e}")
        return _err(f"启动任务失败: {str(e)}")
