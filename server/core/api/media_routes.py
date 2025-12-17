'''
媒体管理路由
通过调用 device_agent 服务接口实现
'''
import json
import os
from datetime import datetime
from flask import Blueprint, request, send_file, abort
from werkzeug.utils import secure_filename

from core.log_config import root_logger
from core.services.playlist_mgr import playlist_mgr
from core.services.media_tool_mgr import media_tool_mgr
from core.models.const import get_media_task_dir, get_media_task_result_dir, ALLOWED_AUDIO_EXTENSIONS
from core.utils import get_media_url, get_media_duration, validate_and_normalize_path, _ok, _err, ensure_directory, is_allowed_audio_file, get_file_info

log = root_logger()
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


# ========== 播放列表本地存储（RDS）接口 ==========

@media_bp.route("/playlist/get", methods=['GET'])
def playlist_get():
    """
    获取当前存储的播放列表集合，支持通过 id 只返回单个列表
    """
    try:
        args = request.args
        # log.info(f"===== [Playlist Get] {json.dumps(args)}")
        playlist_id = args.get("id")
        
        # 如果 id 为空、None 或空字符串，返回整个播放列表集合
        if playlist_id is None or playlist_id in ("None", "null", ""):
            ret = playlist_mgr.get_playlist(None)
        else:
            ret = playlist_mgr.get_playlist(playlist_id)
            if not ret:
                return _err(f"未找到标识为 {playlist_id} 的播放列表")
        return _ok(ret)
    except Exception as e:
        log.error(f"[PLAYLIST] Get error: {e}")
        return _err(f'error: {str(e)}')


@media_bp.route("/playlist/update", methods=['POST'])
def playlist_update():
    """
    更新播放列表
    """
    try:
        log.info("===== [Playlist Update]")
        args = request.get_json(silent=True) or {}
        ret = playlist_mgr.save_playlist(args)
        if ret != 0:
            return _err("更新播放列表失败")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] Update error: {e}")
        return _err(f'error: {str(e)}')


@media_bp.route("/playlist/play", methods=['POST'])
def playlist_play():
    """
    播放播放列表
    """
    try:
        args = request.get_json()
        id = args.get("id")
        if id is None:
            return _err("id is required")
        ret, msg = playlist_mgr.play(id)
        if ret != 0:
            return _err(f"播放播放列表 {id} 失败: {msg}")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] Play error: {e}")
        return _err(f'error: {str(e)}')


@media_bp.route("/playlist/playNext", methods=['POST'])
def playlist_play_next():
    """
    播放下一首
    """
    try:
        args = request.get_json()
        id = args.get("id")
        if id is None:
            return _err("id is required")
        ret, msg = playlist_mgr.play_next(id)
        if ret != 0:
            return _err(f"播放下一首失败: {msg}")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] PlayNext error: {e}")
        return _err(f'error: {str(e)}')


@media_bp.route("/playlist/playPre", methods=['POST'])
def playlist_play_pre():
    """
    播放上一首
    """
    try:
        args = request.get_json()
        id = args.get("id")
        if id is None:
            return _err("id is required")
        ret, msg = playlist_mgr.play_pre(id)
        if ret != 0:
            return _err(f"播放上一首失败: {msg}")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] PlayPre error: {e}")
        return _err(f'error: {str(e)}')


@media_bp.route("/playlist/stop", methods=['POST'])
def playlist_stop():
    """
    停止播放
    """
    try:
        args = request.get_json()
        id = args.get("id")
        if id is None:
            return _err("id is required")
        ret, msg = playlist_mgr.stop(id)
        if ret != 0:
            return _err(f"停止播放失败: {msg}")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] Stop error: {e}")
        return _err(f'error: {str(e)}')


@media_bp.route("/playlist/reload", methods=['POST'])
def playlist_reload():
    """
    重新从 RDS 中加载 playlist 数据
    """
    try:
        log.info("===== [Playlist Reload]")
        ret = playlist_mgr.reload()
        if ret != 0:
            return _err("重新加载播放列表失败")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] Reload error: {e}")
        return _err(f'error: {str(e)}')


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


# ========== 媒体工具接口（音频合成）==========

@media_bp.route("/media/task/create", methods=['POST'])
def create_media_task():
    """
    创建音频合成任务
    参数：
    - name: 任务名称
    """
    try:
        data = request.get_json() or {}
        # 如果没有提供名称，使用当前日期时间作为默认名称
        name = data.get('name', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        code, msg, task_id = media_tool_mgr.create_task(name)
        
        if code != 0:
            return _err(msg)
        
        task_info = media_tool_mgr.get_task(task_id)
        return _ok(task_info)
        
    except Exception as e:
        log.error(f"[MediaTool] 创建任务失败: {e}")
        return _err(f"创建任务失败: {str(e)}")


@media_bp.route("/media/task/upload", methods=['POST'])
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
        
        # 确保目录存在
        from core.models.const import MEDIA_TASK_DIR
        ensure_directory(MEDIA_TASK_DIR)
        task_dir = get_media_task_dir(task_id)
        ensure_directory(task_dir)
        
        # 保存文件
        filename = secure_filename(file.filename)
        file_path = os.path.join(task_dir, filename)
        
        # 如果文件已存在，添加序号
        if os.path.exists(file_path):
            base_name, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(file_path):
                new_filename = f"{base_name}_{counter}{ext}"
                file_path = os.path.join(task_dir, new_filename)
                counter += 1
            filename = os.path.basename(file_path)
        
        file.save(file_path)
        log.info(f"[MediaTool] 文件上传成功: {file_path}")
        
        # 添加到任务
        code, msg = media_tool_mgr.add_file(task_id, file_path, filename)
        if code != 0:
            return _err(msg)
        
        file_info = get_file_info(file_path)
        return _ok(file_info)
        
    except Exception as e:
        log.error(f"[MediaTool] 上传文件失败: {e}")
        return _err(f"上传文件失败: {str(e)}")


@media_bp.route("/media/task/addFileByPath", methods=['POST'])
def add_file_by_path():
    """
    通过文件路径添加文件到任务
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    - file_path: 文件路径（JSON 或 form 参数）
    """
    try:
        data = request.get_json() or request.form.to_dict()
        task_id = data.get('task_id')
        file_path = data.get('file_path')
        
        if not task_id:
            return _err("task_id 参数不能为空")
        
        if not file_path:
            return _err("file_path 参数不能为空")
        
        # 验证文件路径
        file_path = validate_and_normalize_path(file_path)
        if not file_path:
            return _err("文件路径无效")
        
        if not os.path.exists(file_path):
            return _err(f"文件不存在: {file_path}")
        
        if not os.path.isfile(file_path):
            return _err(f"路径不是文件: {file_path}")
        
        filename = os.path.basename(file_path)
        if not is_allowed_audio_file(filename):
            return _err(f"不支持的文件类型，支持的格式: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}")
        
        # 添加到任务
        code, msg = media_tool_mgr.add_file(task_id, file_path, filename)
        if code != 0:
            return _err(msg)
        
        file_info = get_file_info(file_path)
        return _ok(file_info)
        
    except Exception as e:
        log.error(f"[MediaTool] 添加文件失败: {e}")
        return _err(f"添加文件失败: {str(e)}")


@media_bp.route("/media/task/deleteFile", methods=['POST'])
def delete_file():
    """
    从任务中删除文件
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    - file_index: 文件索引（JSON 或 form 参数）
    """
    try:
        data = request.get_json() or request.form.to_dict()
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
        
        code, msg = media_tool_mgr.remove_file(task_id, file_index)
        if code != 0:
            return _err(msg)
        
        return _ok({"message": msg})
        
    except Exception as e:
        log.error(f"[MediaTool] 删除文件失败: {e}")
        return _err(f"删除文件失败: {str(e)}")


@media_bp.route("/media/task/reorderFiles", methods=['POST'])
def reorder_files():
    """
    调整文件顺序
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    - file_indices: 新的文件索引顺序列表（JSON 参数）
    """
    try:
        data = request.get_json() or request.form.to_dict()
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
        
        code, msg = media_tool_mgr.reorder_files(task_id, file_indices)
        if code != 0:
            return _err(msg)
        
        task_info = media_tool_mgr.get_task(task_id)
        return _ok(task_info)
        
    except Exception as e:
        log.error(f"[MediaTool] 调整文件顺序失败: {e}")
        return _err(f"调整文件顺序失败: {str(e)}")


@media_bp.route("/media/task/start", methods=['POST'])
def start_task():
    """
    开始音频合成任务
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = request.get_json() or request.form.to_dict()
        task_id = data.get('task_id')
        
        if not task_id:
            return _err("task_id 参数不能为空")
        
        code, msg = media_tool_mgr.start_task(task_id)
        if code != 0:
            return _err(msg)
        
        task_info = media_tool_mgr.get_task(task_id)
        return _ok(task_info)
        
    except Exception as e:
        log.error(f"[MediaTool] 启动任务失败: {e}")
        return _err(f"启动任务失败: {str(e)}")


@media_bp.route("/media/task/get", methods=['POST'])
def get_task_info():
    """
    获取任务信息
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = request.get_json() or request.form.to_dict()
        task_id = data.get('task_id')
        
        if not task_id:
            return _err("task_id 参数不能为空")
        
        task_info = media_tool_mgr.get_task(task_id)
        if not task_info:
            return _err("任务不存在")
        
        return _ok(task_info)
        
    except Exception as e:
        log.error(f"[MediaTool] 获取任务信息失败: {e}")
        return _err(f"获取任务信息失败: {str(e)}")


@media_bp.route("/media/task/list", methods=['GET'])
def list_all_tasks():
    """
    列出所有任务
    """
    try:
        tasks = media_tool_mgr.list_tasks()
        return _ok({"tasks": tasks})
        
    except Exception as e:
        log.error(f"[MediaTool] 列出任务失败: {e}")
        return _err(f"列出任务失败: {str(e)}")


@media_bp.route("/media/task/delete", methods=['POST'])
def delete_task():
    """
    删除任务
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = request.get_json() or request.form.to_dict()
        task_id = data.get('task_id')
        
        if not task_id:
            return _err("task_id 参数不能为空")
        
        code, msg = media_tool_mgr.delete_task(task_id)
        if code != 0:
            return _err(msg)
        
        return _ok({"message": msg})
        
    except Exception as e:
        log.error(f"[MediaTool] 删除任务失败: {e}")
        return _err(f"删除任务失败: {str(e)}")


@media_bp.route("/media/task/download", methods=['GET'])
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
        
        task_info = media_tool_mgr.get_task(task_id)
        if not task_info:
            return _err("任务不存在")
        
        if task_info['status'] != 'success' or not task_info.get('result_file'):
            return _err("任务未完成或结果文件不存在")
        
        result_file = task_info['result_file']
        if not os.path.exists(result_file):
            return _err("结果文件不存在")
        
        return send_file(result_file, as_attachment=True, download_name='merged.mp3')
        
    except Exception as e:
        log.error(f"[MediaTool] 下载文件失败: {e}")
        return _err(f"下载文件失败: {str(e)}")
