"""
测试小米设备状态获取
使用 MiNAService 获取设备播放状态（包含音量和播放状态）
"""
import os
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.device.mi_device import MiDevice, scan_devices_sync


def test_scan_devices():
    """测试扫描小米设备"""
    print("=" * 50)
    print("测试扫描小米设备")
    print("=" * 50)

    try:
        devices = scan_devices_sync(timeout=5.0)
        print(f"扫描到 {len(devices)} 个设备:")
        for i, device in enumerate(devices, 1):
            print(f"\n设备 {i}:")
            print(f"  名称: {device.get('name', '未知')}")
            print(f"  设备ID: {device.get('deviceID', '未知')}")
            print(f"  MAC地址: {device.get('mac', '未知')}")
            print(f"  米家DID: {device.get('miotDID', '未知')}")
            print(f"  在线状态: {device.get('presence', '未知')}")

        return devices
    except Exception as e:
        print(f"扫描失败: {e}")
        return []


def test_get_status(device_id: str):
    """测试获取设备状态"""
    print("\n" + "=" * 50)
    print(f"测试获取设备状态: {device_id}")
    print("=" * 50)

    try:
        device = MiDevice(device_id)
        code, status = device.get_status()

        if code == 0:
            print("获取状态成功:")
            print(json.dumps(status, indent=2, ensure_ascii=False))

            print("\n状态详情:")
            print(f"  播放状态: {status.get('state', '未知')}")
            print(f"  播放状态码: {status.get('state_code', '未知')}")
            print(f"  状态码: {status.get('status', '未知')}")
            print(f"  音量: {status.get('volume', '未知')}")
            print(f"  当前曲目: {status.get('track', '未知')}")
            print(f"  总时长: {status.get('duration', '未知')}")
            print(f"  播放位置: {status.get('position', '未知')}")
        else:
            error_msg = status.get('error', '未知错误') if isinstance(status, dict) else str(status)
            print(f"获取状态失败: {error_msg}")

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("小米设备状态测试")
    print("=" * 50)

    # 检查环境变量
    mi_user = os.getenv("MI_USER", "")
    mi_pass = os.getenv("MI_PASS", "")

    if not mi_user or not mi_pass:
        print("❌ 错误: 未设置 MI_USER 或 MI_PASS 环境变量")
        print("\n请设置环境变量:")
        print("  export MI_USER=your_username@example.com")
        print("  export MI_PASS=your_password")
        print("\n或者使用临时设置:")
        print("  MI_USER=your_username@example.com MI_PASS=your_password python test/mi_devices.py")
        print()
        return

    print(f"✓ 使用账号: {mi_user[:3]}*** (已隐藏)")

    # 测试1: 扫描设备
    devices = test_scan_devices()

    if not devices:
        print("\n未找到设备，无法继续测试")
        return

    # 测试2: 获取第一个设备的状态
    first_device = devices[0]
    device_id = first_device.get('deviceID')

    if device_id:
        # 测试获取状态（包含音量）
        test_get_status(device_id)

    else:
        print("\n设备ID无效，无法继续测试")


if __name__ == '__main__':
    main()
