'''
媒体管理路由
'''
import os
import urllib.parse
import json
from flask import Blueprint, request
from core.log_config import root_logger
from core.device.bluetooth import (
    get_system_paired_devices_sync,
    connect_device_sync,
    get_bluetooth_mgr
)
from core.db import rds_mgr

log = root_logger()
media_bp = Blueprint('media', __name__)

# 支持的媒体文件扩展名（pygame 主要支持音频格式）
# 注意：pygame 对某些格式的支持取决于系统安装的编解码器
MEDIA_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma'}

# 初始化 pygame mixer
try:
    import pygame
    pygame.mixer.init()
    _pygame_initialized = True
    log.info("[MEDIA] Pygame mixer initialized")
except Exception as e:
    log.error(f"[MEDIA] Failed to initialize pygame mixer: {e}")
    _pygame_initialized = False


def get_media_files(directory):
    """
    获取目录下的所有媒体文件
    :param directory: 目录路径
    :return: 媒体文件列表
    """
    media_files = []
    if not os.path.exists(directory) or not os.path.isdir(directory):
        return media_files
    
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                _, ext = os.path.splitext(item.lower())
                if ext in MEDIA_EXTENSIONS:
                    media_files.append({
                        'name': item,
                        'path': item_path,
                        'size': os.path.getsize(item_path)
                    })
        # 按文件名排序
        media_files.sort(key=lambda x: x['name'])
    except Exception as e:
        log.error(f"[MEDIA] Error listing directory {directory}: {e}")
    
    return media_files


def stop_current_playback():
    """
    停止当前正在播放的音频
    :return: 停止结果
    """
    try:
        if not _pygame_initialized:
            return {"code": -1, "msg": "Pygame not initialized"}
        
        # 检查是否有正在播放的音频
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            log.info("[MEDIA] Stopped playback")
            return {"code": 0, "msg": "Playback stopped"}
        else:
            return {"code": 0, "msg": "No playback in progress"}
    except Exception as e:
        log.error(f"[MEDIA] Error stopping playback: {e}")
        return {"code": -1, "msg": f"Stop failed: {str(e)}"}


def play_media_file(file_path, bluetooth_device=None):
    """
    使用 pygame 播放媒体文件
    :param file_path: 文件路径
    :param bluetooth_device: 蓝牙设备信息（可选）
    :return: 播放结果
    """
    try:
        if not _pygame_initialized:
            return {"code": -1, "msg": "Pygame not initialized"}
        
        # 停止当前正在播放的音频
        stop_result = stop_current_playback()
        if stop_result.get('code') == 0:
            log.info("[MEDIA] Stopped previous playback before starting new one")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {"code": -1, "msg": f"File not found: {file_path}"}
        
        # 使用 pygame.mixer.music 播放音频文件
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            log.info(f"[MEDIA] Playing file: {file_path}")
            return {"code": 0, "msg": "Playing", "file": os.path.basename(file_path)}
        except pygame.error as e:
            log.error(f"[MEDIA] Pygame error playing file {file_path}: {e}")
            return {"code": -1, "msg": f"Play failed: {str(e)}"}
    except Exception as e:
        log.error(f"[MEDIA] Error playing file {file_path}: {e}")
        return {"code": -1, "msg": f"Play failed: {str(e)}"}


@media_bp.route("/media/playDir", methods=['POST'])
def media_play_dir():
    """
    播放目录 获取蓝牙设备 然后播放目录下所有媒体文件
    """
    try:
        log.info("===== [Media Play Directory]")
        
        # 从请求体获取参数（可选）
        args = request.get_json() or {}
        custom_path = args.get('path')  # 可选：允许前端指定路径
        device_address = args.get('device_address')  # 可选：指定设备地址
        
        # 1. 按优先级获取/连接蓝牙设备
        target_device = None
        connected_devices = []
        
        # 优先级1: 使用传入的设备地址
        if device_address:
            log.info(f"Attempting to connect to specified device: {device_address}")
            connect_result = connect_device_sync(device_address, timeout=10.0)
            if connect_result.get('code') == 0:
                target_device = connect_result.get('data', {})
                log.info(f"Successfully connected to specified device: {device_address}")
            else:
                log.warning(f"Failed to connect to specified device {device_address}: {connect_result.get('msg')}")
        
        # 优先级2: 使用系统已配对的设备
        if not target_device:
            connected_devices = get_system_paired_devices_sync()
            if connected_devices:
                target_device = connected_devices[0]
                log.info(f"Using system connected device: {target_device.get('address', 'N/A')}")
        
        # 优先级3: 从 Redis 存档中获取设备并连接
        if not target_device and rds_mgr:
            try:
                data_str = rds_mgr.get_str("SCHELUE_PLAY:bluetooth")
                if data_str:
                    data = json.loads(data_str)
                    # 从存档中获取已连接的设备列表（如果有保存的话）
                    # 这里假设存档中可能保存了设备信息，需要根据实际存档结构调整
                    saved_devices = data.get("connected_devices", [])
                    if saved_devices:
                        # 尝试连接存档中的第一个设备
                        for saved_device in saved_devices:
                            saved_address = saved_device.get('address') if isinstance(saved_device, dict) else saved_device
                            if saved_address:
                                log.info(f"Attempting to connect to saved device: {saved_address}")
                                connect_result = connect_device_sync(saved_address, timeout=10.0)
                                if connect_result.get('code') == 0:
                                    target_device = connect_result.get('data', {})
                                    log.info(f"Successfully connected to saved device: {saved_address}")
                                    break
                                else:
                                    log.warning(f"Failed to connect to saved device {saved_address}: {connect_result.get('msg')}")
            except Exception as e:
                log.warning(f"[MEDIA] Failed to load saved devices from Redis: {e}")
        
        # 如果所有方式都失败，返回错误
        if not target_device:
            return {"code": -1, "msg": "无法获取或连接蓝牙设备，请检查设备连接状态"}
        
        log.info(f"Using bluetooth device: {target_device.get('address', 'N/A')} - {target_device.get('name', 'Unknown')}")
        
        # 2. 获取目录路径：优先使用请求参数，其次从 Redis 获取配置，最后使用默认路径
        selected_path = None
        if custom_path:
            selected_path = custom_path
            log.info(f"Using path from request: {selected_path}")
        else:
            # 从 Redis 获取配置
            if rds_mgr:
                try:
                    data_str = rds_mgr.get_str("SCHELUE_PLAY:bluetooth")
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
        
        # 验证路径
        if not os.path.exists(selected_path) or not os.path.isdir(selected_path):
            return {"code": -1, "msg": f"目录不存在: {selected_path}"}
        
        # 3. 获取目录下的所有媒体文件
        media_files = get_media_files(selected_path)
        if not media_files:
            return {"code": -1, "msg": f"目录下没有找到媒体文件: {selected_path}"}
        
        log.info(f"Found {len(media_files)} media files in {selected_path}")
        
        # 4. 播放文件（这里可以按顺序播放，或者返回文件列表让前端控制）
        # 为了简化，这里返回文件列表和第一个文件的播放结果
        play_results = []
        if media_files:
            first_file = media_files[0]
            play_result = play_media_file(first_file['path'], target_device)
            play_results.append({
                'file': first_file['name'],
                'result': play_result
            })
        
        return {
            "code": 0,
            "msg": "ok",
            "data": {
                "directory": selected_path,
                "bluetooth_device": target_device,
                "media_files": media_files,
                "total_files": len(media_files),
                "play_results": play_results
            }
        }
    except Exception as e:
        log.error(f"[MEDIA] Play directory error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}


@media_bp.route("/media/stop", methods=['POST'])
def media_stop():
    """
    停止当前正在播放的音频
    """
    try:
        log.info("===== [Media Stop]")
        result = stop_current_playback()
        return result
    except Exception as e:
        log.error(f"[MEDIA] Stop error: {e}")
        return {"code": -1, "msg": f'error: {str(e)}'}
