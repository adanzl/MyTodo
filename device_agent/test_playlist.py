#!/usr/bin/env python3
"""
播放列表功能测试脚本
用于测试播放列表配置和播放功能
"""

import sys
import os

# 添加项目路径到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import get_config
from core.playlist_player import play_next_track
from core.log_config import root_logger

log = root_logger()


def test_config():
    """测试配置读取"""
    print("\n========== 测试配置读取 ==========")
    config = get_config()
    
    playlist = config.get_playlist()
    current_index = config.get_current_track_index()
    device_address = config.get_bluetooth_device_address()
    
    print(f"播放列表: {playlist}")
    print(f"当前索引: {current_index}")
    print(f"蓝牙设备地址: {device_address}")
    
    if not playlist:
        print("\n⚠️  播放列表为空！")
        print("请先使用 API 配置播放列表：")
        print("  curl -X POST http://localhost:5000/playlist/update \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{\"playlist\": [\"/path/to/song1.mp3\"], \"device_address\": \"XX:XX:XX:XX:XX:XX\"}'")
        return False
    
    if not device_address:
        print("\n⚠️  未配置蓝牙设备地址！")
        print("请在配置播放列表时提供 device_address 参数")
        return False
    
    # 检查文件是否存在
    invalid_files = []
    for file_path in playlist:
        if not os.path.exists(file_path):
            invalid_files.append(file_path)
    
    if invalid_files:
        print("\n⚠️  以下文件不存在：")
        for file_path in invalid_files:
            print(f"    - {file_path}")
        return False
    
    print("\n✅ 配置检查通过！")
    return True


def test_play():
    """测试播放功能"""
    print("\n========== 测试播放功能 ==========")
    print("正在播放下一首歌曲...\n")
    
    success = play_next_track()
    
    if success:
        print("\n✅ 播放成功！")
        print("注意：播放进程在后台运行，可以使用以下命令查看：")
        print("  ps aux | grep mpg123")
        return True
    else:
        print("\n❌ 播放失败！")
        print("请查看日志了解详细错误信息：")
        print("  tail -f logs/app.log")
        return False


def test_cycle():
    """测试循环播放"""
    print("\n========== 测试循环播放 ==========")
    
    config = get_config()
    playlist = config.get_playlist()
    
    if not playlist:
        print("⚠️  播放列表为空，跳过测试")
        return False
    
    print(f"播放列表共有 {len(playlist)} 首歌曲")
    print("模拟播放整个列表...\n")
    
    for i in range(len(playlist) + 2):  # 多播放几首，测试循环
        current_index = config.get_current_track_index()
        expected_file = playlist[current_index]
        
        print(f"第 {i+1} 次播放:")
        print(f"  - 当前索引: {current_index}")
        print(f"  - 文件: {os.path.basename(expected_file)}")
        
        # 模拟播放后更新索引
        next_index = (current_index + 1) % len(playlist)
        config.set_current_track_index(next_index)
        print(f"  - 下次索引: {next_index}\n")
    
    print("✅ 循环测试完成！")
    return True


def main():
    """主函数"""
    print("=" * 50)
    print("播放列表功能测试")
    print("=" * 50)
    
    # 测试配置
    if not test_config():
        print("\n配置测试失败，请先配置播放列表")
        return 1
    
    # 询问是否继续测试播放
    print("\n" + "=" * 50)
    response = input("是否测试实际播放？(y/n): ").strip().lower()
    
    if response == 'y':
        if not test_play():
            return 1
    else:
        print("跳过播放测试")
    
    # 询问是否测试循环
    print("\n" + "=" * 50)
    response = input("是否测试循环播放逻辑？(y/n): ").strip().lower()
    
    if response == 'y':
        if not test_cycle():
            return 1
    else:
        print("跳过循环测试")
    
    print("\n" + "=" * 50)
    print("所有测试完成！")
    print("=" * 50)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

