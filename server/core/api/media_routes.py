'''
媒体管理路由
通过调用 device_agent 服务接口实现
'''
import json
import os
from flask import Blueprint, request, send_file, abort

from core.log_config import root_logger
from core.services.playlist_mgr import playlist_mgr
from core.utils import get_media_url, get_media_duration, validate_and_normalize_path, _ok, _err

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

@media_bp.route("/getDuration", methods=['GET'])
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
