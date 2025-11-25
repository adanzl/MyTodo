"""
播放列表播放器
用于 cron 定时任务播放播放列表中的歌曲
"""
import os
from core.config import get_config
from core.log_config import root_logger
from core.api.media_routes import get_alsa_bluetooth_device, play_media_file_with_mpg123

log = root_logger()


def play_next_track():
    """
    播放播放列表中的下一首歌曲
    供 cron 定时任务调用
    """
    try:
        config = get_config()
        
        # 获取播放列表
        playlist = config.get_playlist()
        if not playlist:
            log.warning("[PLAYLIST] 播放列表为空")
            return False
        
        # 获取当前播放索引
        current_index = config.get_current_track_index()
        
        # 确保索引有效，如果超出范围则循环到开始
        if current_index >= len(playlist):
            current_index = 0
        
        # 获取当前要播放的文件
        file_path = playlist[current_index]
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            log.error(f"[PLAYLIST] 文件不存在: {file_path}")
            # 跳过这首歌，移动到下一首
            next_index = (current_index + 1) % len(playlist)
            config.set_current_track_index(next_index)
            return False
        
        # 获取蓝牙设备地址
        device_address = config.get_bluetooth_device_address()
        if not device_address:
            log.warning("[PLAYLIST] 未配置蓝牙设备地址")
            return False
        
        # 获取 ALSA 设备
        alsa_device = get_alsa_bluetooth_device(device_address)
        if not alsa_device:
            log.error(f"[PLAYLIST] 无法获取 ALSA 设备: {device_address}")
            return False
        
        log.info(f"[PLAYLIST] 播放第 {current_index + 1}/{len(playlist)} 首: {os.path.basename(file_path)}")
        log.info(f"[PLAYLIST] ALSA 设备: {alsa_device}")
        
        # 使用 media_routes 中的播放函数，确保进程被正确跟踪
        result = play_media_file_with_mpg123(file_path, alsa_device)
        
        if result.get('code') != 0:
            log.error(f"[PLAYLIST] 播放失败: {result.get('msg')}")
            return False
        
        log.info(f"[PLAYLIST] 播放进程已启动 (PID: {result.get('pid')})")
        
        # 更新到下一首
        next_index = (current_index + 1) % len(playlist)
        config.set_current_track_index(next_index)
        log.info(f"[PLAYLIST] 下次将播放第 {next_index + 1}/{len(playlist)} 首")
        
        return True
        
    except Exception as e:
        log.error(f"[PLAYLIST] 播放失败: {str(e)}")
        return False


if __name__ == "__main__":
    # 测试播放
    print("测试播放列表播放器...")
    success = play_next_track()
    if success:
        print("播放成功！")
    else:
        print("播放失败！")

