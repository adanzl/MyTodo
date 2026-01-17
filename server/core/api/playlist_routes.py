"""播放列表管理路由。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from core.config import app_logger
from core.services.playlist_mgr import playlist_mgr
from core.utils import _err, _ok, read_json_from_request

log = app_logger
playlist_bp = Blueprint('playlist', __name__)


@playlist_bp.route("/playlist/get", methods=['GET'])
def playlist_get() -> ResponseReturnValue:
    """获取播放列表集合；支持通过 id 只返回单个列表。"""
    try:
        args = request.args
        playlist_id = args.get("id")

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
def playlist_update() -> ResponseReturnValue:
    """更新单个播放列表（必须包含 id 字段）。"""
    try:
        args: Dict[str, Any] = read_json_from_request()

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
def playlist_update_all() -> ResponseReturnValue:
    """更新整个播放列表集合（覆盖），传入 dict：{playlist_id: playlist_data, ...}。"""
    try:
        args: Dict[str, Any] = read_json_from_request()

        if not args:
            return _err("请求数据不能为空")

        ret = playlist_mgr.save_playlist(args)
        if ret != 0:
            return _err("更新播放列表集合失败")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] UpdateAll error: {e}")
        return _err(f'error: {str(e)}')


def _require_playlist_id(args: Dict[str, Any]) -> tuple[Optional[Any], Optional[ResponseReturnValue]]:
    """从请求体中提取播放列表 id。"""
    pid = args.get("id")
    if pid is None:
        return None, _err("id is required")
    return pid, None


@playlist_bp.route("/playlist/play", methods=['POST'])
def playlist_play() -> ResponseReturnValue:
    """播放播放列表。"""
    try:
        args: Dict[str, Any] = read_json_from_request()
        pid, err = _require_playlist_id(args)
        if err:
            return err

        ret, msg = playlist_mgr.play(pid)
        if ret != 0:
            return _err(f"播放播放列表 {pid} 失败: {msg}")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] Play error: {e}")
        return _err(f'error: {str(e)}')


@playlist_bp.route("/playlist/playNext", methods=['POST'])
def playlist_play_next() -> ResponseReturnValue:
    """播放下一首。"""
    try:
        args: Dict[str, Any] = read_json_from_request()
        pid, err = _require_playlist_id(args)
        if err:
            return err

        ret, msg = playlist_mgr.play_next(pid)
        if ret != 0:
            return _err(f"播放下一首失败: {msg}")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] PlayNext error: {e}")
        return _err(f'error: {str(e)}')


@playlist_bp.route("/playlist/playPre", methods=['POST'])
def playlist_play_pre() -> ResponseReturnValue:
    """播放上一首。"""
    try:
        args: Dict[str, Any] = read_json_from_request()
        pid, err = _require_playlist_id(args)
        if err:
            return err

        ret, msg = playlist_mgr.play_pre(pid)
        if ret != 0:
            return _err(f"播放上一首失败: {msg}")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] PlayPre error: {e}")
        return _err(f'error: {str(e)}')


@playlist_bp.route("/playlist/stop", methods=['POST'])
def playlist_stop() -> ResponseReturnValue:
    """停止播放。"""
    try:
        args: Dict[str, Any] = read_json_from_request()
        pid, err = _require_playlist_id(args)
        if err:
            return err

        ret, msg = playlist_mgr.stop(pid)
        if ret != 0:
            return _err(f"停止播放失败: {msg}")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] Stop error: {e}")
        return _err(f'error: {str(e)}')


@playlist_bp.route("/playlist/reload", methods=['POST'])
def playlist_reload() -> ResponseReturnValue:
    """重新从 RDS 中加载 playlist 数据。"""
    try:
        log.info("===== [Playlist Reload]")
        ret = playlist_mgr.reload()
        if ret != 0:
            return _err("重新加载播放列表失败")
        return _ok()
    except Exception as e:
        log.error(f"[PLAYLIST] Reload error: {e}")
        return _err(f'error: {str(e)}')
