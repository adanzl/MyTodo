'''
媒体管理路由
通过调用 device_agent 服务接口实现
'''
import os
import urllib.parse
import json
from flask import Blueprint, request
from core.log_config import root_logger
from core.device_agent import get_device_agent_client
from core.db import rds_mgr

log = root_logger()
media_bp = Blueprint('media', __name__)



@media_bp.route("/media/stop", methods=['POST'])
def media_stop():
    """
    停止当前正在播放的音频（通过 device_agent 服务）
    """
    try:
        log.info("===== [Media Stop]")
        client = get_device_agent_client()
        result = client.media_stop()
        return result
    except Exception as e:
        log.error(f"[MEDIA] Stop error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}


# ========== 播放列表管理接口 ==========

@media_bp.route("/playlist/update", methods=['POST'])
def playlist_update():
    """
    更新播放列表（通过 device_agent 服务）
    """
    try:
        log.info("===== [Playlist Update]")
        args = request.get_json() or {}
        playlist = args.get('playlist')
        device_address = args.get('device_address')
        
        if not playlist:
            return {"code": -1, "msg": "playlist 参数是必需的"}
        
        if not isinstance(playlist, list):
            return {"code": -1, "msg": "playlist 必须是数组"}
        
        client = get_device_agent_client()
        result = client.playlist_update(playlist, device_address)
        
        # 转换device_agent的响应格式为server端统一格式
        if result.get('success'):
            return {"code": 0, "msg": "ok", "data": result.get('data', {})}
        else:
            return {"code": -1, "msg": result.get('error', '更新失败')}
    except Exception as e:
        log.error(f"[PLAYLIST] Update error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}


@media_bp.route("/playlist/status", methods=['GET'])
def playlist_status():
    """
    获取播放列表状态（通过 device_agent 服务）
    """
    try:
        log.info("===== [Playlist Status]")
        client = get_device_agent_client()
        result = client.playlist_status()
        
        # 转换device_agent的响应格式为server端统一格式
        if result.get('success'):
            return {"code": 0, "msg": "ok", "data": result.get('data', {})}
        else:
            return {"code": -1, "msg": result.get('error', '获取状态失败')}
    except Exception as e:
        log.error(f"[PLAYLIST] Status error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}


@media_bp.route("/playlist/play", methods=['POST'])
def playlist_play():
    """
    播放当前播放列表中的歌曲（通过 device_agent 服务）
    """
    try:
        log.info("===== [Playlist Play]")
        client = get_device_agent_client()
        result = client.playlist_play()
        
        # 转换device_agent的响应格式为server端统一格式
        if result.get('success'):
            return {"code": 0, "msg": "ok", "data": result.get('data', {})}
        else:
            return {"code": -1, "msg": result.get('error', '播放失败')}
    except Exception as e:
        log.error(f"[PLAYLIST] Play error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}


@media_bp.route("/playlist/playNext", methods=['POST'])
def playlist_play_next():
    """
    播放下一首歌曲（通过 device_agent 服务）
    """
    try:
        log.info("===== [Playlist Play Next]")
        client = get_device_agent_client()
        result = client.playlist_play_next()
        
        # 转换device_agent的响应格式为server端统一格式
        if result.get('success'):
            return {"code": 0, "msg": "ok", "data": result.get('data', {})}
        else:
            return {"code": -1, "msg": result.get('error', '播放下一首失败')}
    except Exception as e:
        log.error(f"[PLAYLIST] Play Next error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}


@media_bp.route("/playlist/stop", methods=['POST'])
def playlist_stop():
    """
    停止播放列表播放（通过 device_agent 服务）
    """
    try:
        log.info("===== [Playlist Stop]")
        client = get_device_agent_client()
        result = client.playlist_stop()
        
        # media/stop 返回的格式是 {"code": 0, "msg": "..."}
        # 直接返回即可，保持格式一致
        return result
    except Exception as e:
        log.error(f"[PLAYLIST] Stop error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}


# ========== Cron 定时任务接口 ==========

@media_bp.route("/cron/status", methods=['GET'])
def cron_status():
    """
    获取 Cron 定时任务状态（通过 device_agent 服务）
    """
    try:
        log.info("===== [Cron Status]")
        client = get_device_agent_client()
        result = client.cron_get_status()
        
        # 转换device_agent的响应格式为server端统一格式
        if result.get('success'):
            return {"code": 0, "msg": "ok", "data": result.get('data', {})}
        else:
            return {"code": -1, "msg": result.get('error', '获取状态失败')}
    except Exception as e:
        log.error(f"[CRON] Status error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}


@media_bp.route("/cron/update", methods=['POST'])
def cron_update():
    """
    更新 Cron 定时任务配置（通过 device_agent 服务）
    """
    try:
        log.info("===== [Cron Update]")
        args = request.get_json() or {}
        enabled = args.get('enabled')
        expression = args.get('expression')
        command = args.get('command')
        
        client = get_device_agent_client()
        result = client.cron_update(enabled=enabled, expression=expression, command=command)
        
        # 转换device_agent的响应格式为server端统一格式
        if result.get('success'):
            return {"code": 0, "msg": "ok", "data": result.get('data', {})}
        else:
            return {"code": -1, "msg": result.get('error', '更新失败')}
    except Exception as e:
        log.error(f"[CRON] Update error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}
