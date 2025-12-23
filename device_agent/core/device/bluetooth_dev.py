'''
蓝牙设备类
'''
from typing import Optional
from bleak import BleakClient


class BluetoothDev:
    """蓝牙设备类"""

    def __init__(self, address: str, name: str = "", metadata: dict = None):
        self.address = address
        self.name = name or address
        self.metadata = metadata or {}
        self.connected = False
        self.client: Optional[BleakClient] = None

    def to_dict(self):
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
            return {
                'hex': obj.hex(),
                'length': len(obj)
            }
        elif isinstance(obj, dict):
            return {str(k): self._ensure_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._ensure_json_serializable(item) for item in obj]
        elif hasattr(obj, '__str__') and not isinstance(obj, (str, int, float, bool, type(None))):
            return str(obj)
        else:
            return obj

