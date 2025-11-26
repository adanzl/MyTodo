'''
媒体管理路由
通过调用 device_agent 服务接口实现
'''
import json
import os
import socket
from flask import Blueprint, request, send_file, abort
from urllib.parse import quote

from core.log_config import root_logger
from core.models.playlist import playlist_mgr

log = root_logger()
media_bp = Blueprint('media', __name__)


def _ok(data=None):
    return {"code": 0, "msg": "ok", "data": data}


def _err(message: str):
    return {"code": -1, "msg": message}



# ========== 播放列表本地存储（RDS）接口 ==========

@media_bp.route("/playlist/get", methods=['GET'])
def playlist_get():
    """
    获取当前存储的播放列表集合，支持通过 id 只返回单个列表
    """
    try:
        args = request.args
        log.info("===== [Playlist Get] " + json.dumps(args))
        id = args.get("id")
        ret = playlist_mgr.get_playlist(id)
        if ret is None:
            return _err(f"未找到标识为 {id} 的播放列表")
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
            return _err(f"更新播放列表失败")
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
        ret = playlist_mgr.play_next(id)
        if ret != 0:
            return _err(f"播放下一首失败")
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


# ========== 媒体文件服务接口（用于 DLNA 播放）==========

def _get_local_ip():
    """获取本机局域网IP地址"""
    try:
        # 连接到一个远程地址来获取本机IP（不会实际发送数据）
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # 如果失败，尝试获取主机名对应的IP
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def _get_media_server_url():
    """获取媒体文件服务器的完整URL"""
    # 返回固定的服务器地址和端口
    return "http://192.168.50.172:8848"


@media_bp.route("/media/files/<path:filepath>", methods=['GET'])
def serve_media_file(filepath):
    """
    提供媒体文件访问服务（用于 DLNA 播放）
    :param filepath: 文件路径（相对于根目录，如 mnt/ext_base/audio/xiaopingguo.mp3）
    """
    try:
        # 安全处理：移除路径中的危险字符
        # 将 URL 编码的路径解码
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
        mimetype_map = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.flac': 'audio/flac',
            '.aac': 'audio/aac',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4',
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
        }
        mimetype = mimetype_map.get(ext, 'application/octet-stream')
        
        log.info(f"[MEDIA] Serving file: {filepath} (MIME: {mimetype})")
        return send_file(filepath, mimetype=mimetype)
    except Exception as e:
        log.error(f"[MEDIA] Error serving file {filepath}: {e}")
        abort(500)


def get_media_url(local_path: str) -> str:
    """
    将本地文件路径转换为可通过 HTTP 访问的 URL
    :param local_path: 本地文件路径，如 /mnt/ext_base/audio/xiaopingguo.mp3
    :return: HTTP URL，如 http://192.168.1.100:8000/api/media/files/mnt/ext_base/audio/xiaopingguo.mp3
    """
    try:
        # 移除路径开头的 /
        if local_path.startswith('/'):
            filepath = local_path[1:]
        else:
            filepath = local_path
        
        # URL 编码路径
        encoded_path = '/'.join(quote(part, safe='') for part in filepath.split('/'))
        
        # 获取服务器URL（使用固定地址）
        base_url = _get_media_server_url()
        
        # 根据 main.py 中的 DispatcherMiddleware 配置，应用挂载在 /api 下
        # 所以完整路径是 /api/media/files/
        media_url = f"{base_url}/api/media/files/{encoded_path}"
        log.debug(f"[MEDIA] Converted {local_path} to {media_url}")
        return media_url
    except Exception as e:
        log.error(f"[MEDIA] Error converting path {local_path}: {e}")
        return local_path
