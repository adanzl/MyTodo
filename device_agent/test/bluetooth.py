import sys
import os
from time import sleep

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.service.bluetooth_mgr import bluetooth_mgr

if __name__ == "__main__":
    # 测试代码
    print("======================== Bluetooth Manager Test ================================")
    # 测试扫描
    # devices = bluetooth_mgr.scan_devices_sync(timeout=3.0)
    # print(f"Found {len(devices)} devices")
    # for device in devices:
    #     print(f"【{device['address']}】{device['name']}")
    # 测试获取系统已连接的设备
    # connected_devices = bluetooth_mgr.get_connected_devices()
    # print(f"Found {len(connected_devices)} connected devices")
    # for device in connected_devices:
    #     print(device)
    device_address = "90:FB:5D:E9:F0:9B"
    info = bluetooth_mgr.get_info(device_address)
    print(f"{device_address} connected: {info['data']['connected']}")
    print(bluetooth_mgr.disconnect_device_sync(device_address))
    info = bluetooth_mgr.get_info(device_address)
    print(f"{device_address} connected: {info['data']['connected']}")
    sleep(5)
    print(bluetooth_mgr.connect_device_sync(device_address))
    info = bluetooth_mgr.get_info(device_address)
    print(f"{device_address} connected: {info['data']['connected']}")
