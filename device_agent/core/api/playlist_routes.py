"""
播放列表管理路由
"""
import os
from flask import Blueprint, jsonify, request
from core.log_config import root_logger
from core.config import get_config
from core.playlist_player import play_next_track
from core.api.media_routes import get_playback_status

log = root_logger()
playlist_bp = Blueprint('playlist', __name__)


@playlist_bp.route("/playlist/update", methods=['POST'])
def playlist_update():
    """更新播放列表"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请提供配置数据'
            }), 400
        
        config = get_config()
        
        # 获取参数
        playlist = data.get('playlist')  # 音乐文件路径列表
        device_address = data.get('device_address')  # 蓝牙设备地址（可选）
        
        # 验证播放列表
        if playlist is None:
            return jsonify({
                'success': False,
                'error': 'playlist 参数是必需的'
            }), 400
        
        if not isinstance(playlist, list):
            return jsonify({
                'success': False,
                'error': 'playlist 必须是数组'
            }), 400
        
        # 验证文件是否存在
        invalid_files = []
        for file_path in playlist:
            if not isinstance(file_path, str):
                return jsonify({
                    'success': False,
                    'error': 'playlist 中的每一项必须是字符串路径'
                }), 400
            if not os.path.exists(file_path):
                invalid_files.append(file_path)
        
        if invalid_files:
            return jsonify({
                'success': False,
                'error': f'以下文件不存在: {", ".join(invalid_files)}'
            }), 400
        
        # 更新播放列表
        success = config.set_playlist(playlist)
        if not success:
            return jsonify({
                'success': False,
                'error': '保存播放列表失败'
            }), 500
        
        # 如果提供了蓝牙设备地址，保存它
        if device_address:
            config.set_bluetooth_device_address(device_address)
        
        # 重置播放索引到0
        config.set_current_track_index(0)
        
        log.info(f"播放列表已更新，共 {len(playlist)} 首歌曲")
        
        return jsonify({
            'success': True,
            'message': '播放列表已更新',
            'data': {
                'playlist': playlist,
                'total': len(playlist),
                'device_address': device_address,
                'current_index': 0
            }
        })
        
    except Exception as e:
        log.error(f"更新播放列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@playlist_bp.route("/playlist/status", methods=['GET'])
def playlist_status():
    """获取播放列表状态"""
    try:
        config = get_config()
        
        playlist = config.get_playlist()
        current_index = config.get_current_track_index()
        device_address = config.get_bluetooth_device_address()
        
        current_file = None
        if playlist and 0 <= current_index < len(playlist):
            current_file = playlist[current_index]
        
        # 获取播放状态
        playback_status = get_playback_status()
        
        return jsonify({
            'success': True,
            'data': {
                'playlist': playlist,
                'total': len(playlist),
                'current_index': current_index,
                'current_file': current_file,
                'device_address': device_address,
                'is_playing': playback_status['is_playing'],
                'playing_pid': playback_status['pid']
            }
        })
        
    except Exception as e:
        log.error(f"获取播放列表状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@playlist_bp.route("/playlist/play", methods=['POST'])
def playlist_play():
    """播放当前播放列表中的歌曲（立即播放，不等待定时任务）"""
    try:
        log.info("===== [Playlist Play] 手动触发播放列表播放")
        
        # 检查播放列表是否存在
        config = get_config()
        playlist = config.get_playlist()
        
        if not playlist:
            return jsonify({
                'success': False,
                'error': '播放列表为空，请先配置播放列表'
            }), 400
        
        device_address = config.get_bluetooth_device_address()
        if not device_address:
            return jsonify({
                'success': False,
                'error': '未配置蓝牙设备地址'
            }), 400
        
        current_index = config.get_current_track_index()
        
        # 调用播放函数
        success = play_next_track()
        
        if success:
            # 播放成功后，获取更新后的状态
            new_index = config.get_current_track_index()
            played_file = playlist[current_index] if current_index < len(playlist) else None
            
            return jsonify({
                'success': True,
                'message': '播放成功',
                'data': {
                    'played_index': current_index,
                    'played_file': played_file,
                    'next_index': new_index,
                    'playlist_total': len(playlist)
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '播放失败，请查看日志了解详情'
            }), 500
        
    except Exception as e:
        log.error(f"播放列表播放失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@playlist_bp.route("/playlist/playNext", methods=['POST'])
def playlist_play_next():
    """播放下一首歌曲（自动循环：如果是最后一首则播放第一首）"""
    try:
        log.info("===== [Playlist Play Next] 播放下一首歌曲")
        
        # 检查播放列表是否存在
        config = get_config()
        playlist = config.get_playlist()
        
        if not playlist:
            return jsonify({
                'success': False,
                'error': '播放列表为空，请先配置播放列表'
            }), 400
        
        device_address = config.get_bluetooth_device_address()
        if not device_address:
            return jsonify({
                'success': False,
                'error': '未配置蓝牙设备地址'
            }), 400
        
        current_index = config.get_current_track_index()
        
        # 调用播放函数（内部已实现循环逻辑）
        success = play_next_track()
        
        if success:
            # 播放成功后，获取更新后的状态
            new_index = config.get_current_track_index()
            played_file = playlist[current_index] if current_index < len(playlist) else None
            next_file = playlist[new_index] if new_index < len(playlist) else None
            
            # 判断是否循环到第一首
            is_looped = (current_index == len(playlist) - 1 and new_index == 0)
            
            return jsonify({
                'success': True,
                'message': '播放成功' + (' (已循环到第一首)' if is_looped else ''),
                'data': {
                    'played_index': current_index,
                    'played_file': played_file,
                    'next_index': new_index,
                    'next_file': next_file,
                    'playlist_total': len(playlist),
                    'is_looped': is_looped
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '播放失败，请查看日志了解详情'
            }), 500
        
    except Exception as e:
        log.error(f"播放下一首失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

