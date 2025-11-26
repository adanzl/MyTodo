'''
媒体管理路由
通过调用 device_agent 服务接口实现
'''
import json
from flask import Blueprint, request

from core.log_config import root_logger
from core.device.agent import get_device_agent_client
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
        args = request.get_json()
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
        ret = playlist_mgr.stop(id)
        if ret != 0:
            return _err(f"停止播放失败")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] Stop error: {e}")
        return _err(f'error: {str(e)}')
