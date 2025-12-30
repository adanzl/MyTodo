'''
蓝牙设备类
'''
from typing import Dict, Optional

from bleak import BleakClient


class BluetoothDev:
    """蓝牙设备类"""

    def __init__(self, address: str, name: str = "", metadata: dict = None):
        self.address = address
        self.name = name or address
        self.metadata = metadata or {}
        self.connected = False
        self.client: Optional[BleakClient] = None

    def to_dict(self) -> Dict:
        """转换为字典，确保所有数据都是 JSON 可序列化的"""
        return {
            "address": str(self.address),
            "name": str(self.name) if self.name else str(self.address),
            "connected": bool(self.connected),
            "metadata": self._ensure_json_serializable(self.metadata)
        }

    def _ensure_json_serializable(self, obj):
        """递归确保对象是 JSON 可序列化的"""
        if isinstance(obj, bytes):
            return {'hex': obj.hex(), 'length': len(obj)}
        elif isinstance(obj, dict):
            return {str(k): self._ensure_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._ensure_json_serializable(item) for item in obj]
        elif hasattr(obj, '__str__') and not isinstance(obj, (str, int, float, bool, type(None))):
            return str(obj)
        else:
            return obj


# 从 services 导入 BluetoothMgr 和全局实例
from core.services.bluetooth_mgr import bluetooth_mgr

if __name__ == "__main__":
    # 测试代码
    print("Bluetooth Manager Test")
    devices = bluetooth_mgr.scan_devices_sync(timeout=3.0)
    print(f"Found {len(devices)} devices")
    for device in devices:
        print(f"【{device['address']}】{device['name']}")

    connected_devices = bluetooth_mgr.get_system_paired_devices()
    print(f"Found {len(connected_devices)} connected devices")
    for device in connected_devices:
        print(f"【{device.get('address', 'N/A')}】{device.get('name', 'Unknown')}")
