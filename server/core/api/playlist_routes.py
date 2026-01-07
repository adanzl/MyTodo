'''
播放列表管理路由
'''
from flask import Blueprint, request

from core.log_config import app_logger
from core.services.playlist_mgr import playlist_mgr
from core.utils import _ok, _err, read_json_from_request

log = app_logger
playlist_bp = Blueprint('playlist', __name__)

# ========== 播放列表本地存储（RDS）接口 ==========


@playlist_bp.route("/playlist/get", methods=['GET'])
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


@playlist_bp.route("/playlist/update", methods=['POST'])
def playlist_update():
    """
    更新单个播放列表
    传入单个播放列表数据，必须包含 id 字段
    """
    try:
        args = read_json_from_request()

        if not args:
            return _err("请求数据不能为空")

        playlist_id = args.get("id")
        if not playlist_id:
            return _err("播放列表 id 不能为空")

        ret = playlist_mgr.update_single_playlist(args)
        if ret != 0:
            return _err("更新播放列表失败")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] Update error: {e}", exc_info=True)
        return _err(f'error: {str(e)}')


@playlist_bp.route("/playlist/updateAll", methods=['POST'])
def playlist_update_all():
    """
    更新整个播放列表集合（覆盖）
    传入字典格式 {playlist_id: playlist_data, ...}
    """
    try:
        args = read_json_from_request()

        if not args:
            return _err("请求数据不能为空")

        ret = playlist_mgr.save_playlist(args)
        if ret != 0:
            return _err("更新播放列表集合失败")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] UpdateAll error: {e}")
        return _err(f'error: {str(e)}')


@playlist_bp.route("/playlist/play", methods=['POST'])
def playlist_play():
    """
    播放播放列表
    """
    try:
        args = read_json_from_request()
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


@playlist_bp.route("/playlist/playNext", methods=['POST'])
def playlist_play_next():
    """
    播放下一首
    """
    try:
        args = read_json_from_request()
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


@playlist_bp.route("/playlist/playPre", methods=['POST'])
def playlist_play_pre():
    """
    播放上一首
    """
    try:
        args = read_json_from_request()
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


@playlist_bp.route("/playlist/stop", methods=['POST'])
def playlist_stop():
    """
    停止播放
    """
    try:
        args = read_json_from_request()
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


@playlist_bp.route("/playlist/reload", methods=['POST'])
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
