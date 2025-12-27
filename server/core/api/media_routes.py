'''
媒体管理路由
通过调用 device_agent 服务接口实现
'''
import json
import os
import shutil
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


def _get_unique_filepath(directory: str, base_name: str, extension: str) -> str:
    """
    生成唯一的文件路径，如果文件已存在则添加序号
    
    :param directory: 目标目录
    :param base_name: 基础文件名（不含扩展名）
    :param extension: 文件扩展名（包含点号，如 '.mp3'）
    :return: 唯一的文件路径
    """
    filename = f"{base_name}{extension}"
    file_path = os.path.join(directory, filename)

    if os.path.exists(file_path):
        counter = 1
        while os.path.exists(file_path):
            filename = f"{base_name}_{counter}{extension}"
            file_path = os.path.join(directory, filename)
            counter += 1

    return file_path


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
    更新单个播放列表
    传入单个播放列表数据，必须包含 id 字段
    """
    try:
        log.info("===== [Playlist Update] START")
        log.info(f"===== [Playlist Update] STEP0: 请求信息 Content-Length={request.content_length}, Content-Type={request.content_type}")
        
        # 使用 request.stream 手动读取数据，避免 request.get_json() 阻塞
        log.info("===== [Playlist Update] STEP1: 使用 stream 读取请求数据")
        import time
        import json as json_lib
        start_time = time.time()
        
        try:
            log.info("===== [Playlist Update] STEP1.1: 读取 request.stream")
            # 使用 request.stream 读取原始数据
            content_length = request.content_length or 0
            if content_length > 0:
                raw_data = request.stream.read(content_length)
                log.info(f"===== [Playlist Update] STEP1.1 SUCCESS: 读取了 {len(raw_data)} 字节")
            else:
                # 如果没有 Content-Length，尝试读取所有数据
                log.info("===== [Playlist Update] STEP1.1: Content-Length 为 0，尝试读取所有数据")
                raw_data = request.stream.read()
                log.info(f"===== [Playlist Update] STEP1.1 SUCCESS: 读取了 {len(raw_data)} 字节")
            
            log.info("===== [Playlist Update] STEP1.2: 解析 JSON")
            if raw_data:
                args = json_lib.loads(raw_data.decode('utf-8'))
                elapsed = time.time() - start_time
                log.info(f"===== [Playlist Update] STEP1 SUCCESS: 耗时={elapsed:.3f}s, args type={type(args)}, args keys count={len(args) if isinstance(args, dict) else 0}")
                if isinstance(args, dict) and args:
                    log.info(f"===== [Playlist Update] STEP1 SUCCESS: 前5个keys={list(args.keys())[:5]}")
            else:
                log.warning("===== [Playlist Update] STEP1 FAILED: 没有读取到数据")
                args = {}
        except Exception as e:
            elapsed = time.time() - start_time
            log.error(f"===== [Playlist Update] STEP1 EXCEPTION: 耗时={elapsed:.3f}s, error={e}", exc_info=True)
            # 降级到 request.get_json()
            try:
                log.info("===== [Playlist Update] STEP1 FALLBACK: 尝试使用 request.get_json()")
                args = request.get_json(silent=True) or {}
                log.info(f"===== [Playlist Update] STEP1 FALLBACK SUCCESS: args keys count={len(args) if isinstance(args, dict) else 0}")
            except Exception as e2:
                log.error(f"===== [Playlist Update] STEP1 FALLBACK EXCEPTION: {e2}", exc_info=True)
                args = {}

        if not args:
            log.warning("===== [Playlist Update] STEP1 FAILED: 请求数据为空")
            return _err("请求数据不能为空")

        playlist_id = args.get("id")
        if not playlist_id:
            log.warning(f"===== [Playlist Update] STEP2 FAILED: 播放列表 id 为空")
            return _err("播放列表 id 不能为空")
        log.info(f"===== [Playlist Update] STEP2 SUCCESS: playlist_id={playlist_id}")

        log.info(f"===== [Playlist Update] STEP3: 调用 update_single_playlist playlist_id={playlist_id}")
        ret = playlist_mgr.update_single_playlist(args)
        log.info(f"===== [Playlist Update] STEP3 SUCCESS: ret={ret}")
        
        if ret != 0:
            log.warning(f"===== [Playlist Update] STEP4 FAILED: 更新播放列表失败 ret={ret}")
            return _err("更新播放列表失败")
        log.info("===== [Playlist Update] END: SUCCESS")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] Update error: {e}", exc_info=True)
        return _err(f'error: {str(e)}')


@media_bp.route("/playlist/updateAll", methods=['POST'])
def playlist_update_all():
    """
    更新整个播放列表集合（覆盖）
    传入字典格式 {playlist_id: playlist_data, ...}
    """
    try:
        log.info("===== [Playlist Update All]")
        args = request.get_json(silent=True) or {}

        if not args:
            return _err("请求数据不能为空")

        ret = playlist_mgr.save_playlist(args)
        if ret != 0:
            return _err("更新播放列表集合失败")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] UpdateAll error: {e}")
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

        # 确保任务目录存在
        task_dir = get_media_task_dir(task_id)
        ensure_directory(task_dir)

        # 保存文件，如果文件已存在则添加序号
        filename = secure_filename(file.filename)
        base_name, ext = os.path.splitext(filename)
        file_path = _get_unique_filepath(task_dir, base_name, ext)
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


@media_bp.route("/media/task/save", methods=['POST'])
def save_result():
    """
    转存合成结果文件到指定目录
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    - target_path: 目标目录路径（JSON 或 form 参数）
    """
    try:
        data = request.get_json() or request.form.to_dict()
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
        task_info = media_tool_mgr.get_task(task_id)
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
        target_file = _get_unique_filepath(target_path, task_id, ext)

        # 复制文件到目标目录
        shutil.copy2(result_file, target_file)
        log.info(f"[MediaTool] 文件转存成功: {result_file} -> {target_file}")

        return _ok({"target_file": target_file, "message": "转存成功"})

    except Exception as e:
        log.error(f"[MediaTool] 转存文件失败: {e}")
        return _err(f"转存文件失败: {str(e)}")
