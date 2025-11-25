"""
播放列表播放器
用于 cron 定时任务播放播放列表中的歌曲
"""
import os
import subprocess
import time
from core.config import get_config
from core.log_config import root_logger
from core.api.media_routes import get_alsa_bluetooth_device

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
        
        # 构建 mpg123 命令
        cmd = ['mpg123', '-a', alsa_device, file_path]
        
        # 准备环境变量
        env = os.environ.copy()
        if 'XDG_RUNTIME_DIR' not in env:
            import pwd
            try:
                env['XDG_RUNTIME_DIR'] = f"/run/user/{os.getuid()}"
            except:
                pass
        
        if 'HOME' not in env:
            try:
                import pwd
                user_info = pwd.getpwuid(os.getuid())
                env['HOME'] = user_info.pw_dir
            except:
                pass
        
        # 启动播放进程
        log.info(f"[PLAYLIST] 执行命令: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True
        )
        
        # 等待一小段时间检查进程是否立即退出
        time.sleep(0.1)
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            log.error(f"[PLAYLIST] mpg123 启动失败: {stderr}")
            return False
        
        log.info(f"[PLAYLIST] 播放进程已启动 (PID: {process.pid})")
        
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

