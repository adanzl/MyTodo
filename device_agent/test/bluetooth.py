import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.service.bluetooth_mgr import bluetooth_mgr

if __name__ == "__main__":
    # 测试代码
    print("Bluetooth Manager Test")
    # 测试扫描
    devices = bluetooth_mgr.scan_devices_sync(timeout=3.0)
    print(f"Found {len(devices)} devices")
    for device in devices:
        print(f"【{device['address']}】{device['name']}")
    # 测试获取系统已连接的设备
    connected_devices = bluetooth_mgr.get_system_paired_devices()
    print(f"Found {len(connected_devices)} connected devices")
    for device in connected_devices:
        print(f"【{device.get('address', 'N/A')}】{device.get('name', 'Unknown')}")