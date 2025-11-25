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


@media_bp.route("/media/playDir", methods=['POST'])
def media_play_dir():
    """
    播放目录（通过 device_agent 服务）
    使用播放列表功能，将目录下的文件添加到播放列表并开始播放
    """
    try:
        log.info("===== [Media Play Directory]")
        
        # 从请求体获取参数（可选）
        args = request.get_json() or {}
        custom_path = args.get('path')  # 可选：允许前端指定路径
        device_address = args.get('device_address')  # 可选：指定设备地址
        
        client = get_device_agent_client()
        
        # 1. 获取/连接蓝牙设备
        target_device_address = None
        
        # 优先级1: 使用传入的设备地址
        if device_address:
            log.info(f"Using specified device: {device_address}")
            target_device_address = device_address
        else:
            # 优先级2: 获取已连接的设备
            connected_result = client.bluetooth_get_connected()
            if connected_result.get('code') == 0:
                connected_devices = connected_result.get('data', [])
                if connected_devices:
                    # 查找已连接的设备
                    for device in connected_devices:
                        if device.get('connected'):
                            target_device_address = device.get('address')
                            log.info(f"Using connected device: {target_device_address}")
                            break
                    
                    # 如果没有已连接的，使用第一个设备
                    if not target_device_address and connected_devices:
                        target_device_address = connected_devices[0].get('address')
                        log.info(f"Using first paired device: {target_device_address}")
            
            # 优先级3: 从 Redis 存档中获取设备
            if not target_device_address and rds_mgr:
                try:
                    data_str = rds_mgr.get_str("SCHEDULE_PLAY:bluetooth")
                    if data_str:
                        data = json.loads(data_str)
                        saved_devices = data.get("connected_devices", [])
                        if saved_devices:
                            saved_device = saved_devices[0] if isinstance(saved_devices, list) else saved_devices
                            if isinstance(saved_device, dict):
                                target_device_address = saved_device.get('address')
                            else:
                                target_device_address = saved_device
                            if target_device_address:
                                log.info(f"Using saved device: {target_device_address}")
                except Exception as e:
                    log.warning(f"[MEDIA] Failed to load saved devices from Redis: {e}")
        
        if not target_device_address:
            return {"code": -1, "msg": "无法获取蓝牙设备，请先连接设备"}
        
        # 2. 获取目录路径
        selected_path = None
        if custom_path:
            selected_path = custom_path
            log.info(f"Using path from request: {selected_path}")
        else:
            # 从 Redis 获取配置
            if rds_mgr:
                try:
                    data_str = rds_mgr.get_str("SCHEDULE_PLAY:bluetooth")
                    if data_str:
                        data = json.loads(data_str)
                        selected_path = data.get("selected_path", "")
                        log.info(f"Loaded selected_path from Redis: {selected_path}")
                except Exception as e:
                    log.warning(f"[MEDIA] Failed to load config from Redis: {e}")
            
            # 如果没有配置，使用默认路径
            if not selected_path:
                selected_path = "/mnt"
                log.info(f"Using default path: {selected_path}")
        
        # 验证路径（在server端验证，因为文件在server端）
        if not os.path.exists(selected_path) or not os.path.isdir(selected_path):
            return {"code": -1, "msg": f"目录不存在: {selected_path}"}
        
        # 3. 获取目录下的所有媒体文件
        media_files = []
        try:
            for item in os.listdir(selected_path):
                item_path = os.path.join(selected_path, item)
                if os.path.isfile(item_path):
                    _, ext = os.path.splitext(item.lower())
                    # 支持的媒体文件扩展名
                    if ext in {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma'}:
                        media_files.append(item_path)
            # 按文件名排序
            media_files.sort()
        except Exception as e:
            log.error(f"[MEDIA] Error listing directory {selected_path}: {e}")
            return {"code": -1, "msg": f"读取目录失败: {str(e)}"}
        
        if not media_files:
            return {"code": -1, "msg": f"目录下没有找到媒体文件: {selected_path}"}
        
        log.info(f"Found {len(media_files)} media files in {selected_path}")
        
        # 4. 更新播放列表并开始播放
        update_result = client.playlist_update(media_files, target_device_address)
        if update_result.get('success') != True:
            return {"code": -1, "msg": f"更新播放列表失败: {update_result.get('error', '未知错误')}"}
        
        # 5. 开始播放
        play_result = client.playlist_play()
        if play_result.get('success') != True:
            return {"code": -1, "msg": f"播放失败: {play_result.get('error', '未知错误')}"}
        
        return {
            "code": 0,
            "msg": "ok",
            "data": {
                "directory": selected_path,
                "device_address": target_device_address,
                "total_files": len(media_files),
                "play_info": play_result.get('data', {})
            }
        }
    except Exception as e:
        log.error(f"[MEDIA] Play directory error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}


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
