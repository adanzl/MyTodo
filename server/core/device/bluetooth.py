'''
蓝牙设备类
'''
from typing import Dict, Optional, Any, Union

from bleak import BleakClient

from core.device.base import DeviceBase


class BluetoothDev(DeviceBase):
    """蓝牙设备类"""

    def __init__(self, address: str, name: str = "", metadata: Optional[Dict[str, Any]] = None):
        super().__init__(name=name)
        self.address = address
        self.metadata = metadata or {}
        self.connected = False
        self.client: Optional[BleakClient] = None

    def to_dict(self) -> Dict[str, Any]:
        """将设备信息转换为可序列化为 JSON 的字典。

        Returns:
            Dict[str, Any]: 包含设备地址、名称、连接状态和元数据的字典。
        """
        return {
            "address": str(self.address),
            "name": str(self.name) if self.name else str(self.address),
            "connected": bool(self.connected),
            "metadata": self._ensure_json_serializable(self.metadata)
        }

    def _ensure_json_serializable(self, obj: Any) -> Union[Dict[str, Any], list, str, int, float, bool, None]:
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

    def play(self, url: str) -> tuple[int, str]:
        """播放媒体文件"""
        return 0, "ok"

    def stop(self) -> tuple[int, str]:
        """停止播放"""
        return 0, "ok"

    def get_status(self) -> tuple[int, dict]:
        """获取设备状态"""
        return 0, {"status": "ok"}

    def get_volume(self) -> tuple[int, int]:
        """获取设备音量"""
        return 0, 100

    def set_volume(self, volume: int) -> tuple[int, str]:
        """设置设备音量"""
        return 0, "ok"


# 注意：不要在模块级别导入 bluetooth_mgr，避免循环导入
# bluetooth_mgr 在需要时通过延迟导入获取

if __name__ == "__main__":
    # 测试代码（延迟导入避免循环导入）
    from core.services.bluetooth_mgr import bluetooth_mgr
    print("Bluetooth Manager Test")
    devices = bluetooth_mgr.scan_devices_sync(timeout=3.0)
    print(f"Found {len(devices)} devices")
    for device in devices:
        print(f"【{device['address']}】{device['name']}")

    connected_devices = bluetooth_mgr.get_system_paired_devices()
    print(f"Found {len(connected_devices)} connected devices")
    for device in connected_devices:
        print(f"【{device.get('address', 'N/A')}】{device.get('name', 'Unknown')}")
