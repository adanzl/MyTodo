'''
蓝牙设备管理
'''
import asyncio
import json
import os
import platform
import shutil
from typing import Any, Dict, List, Optional

from core.utils import run_async
from core.log_config import root_logger

log = root_logger()

# 尝试使用 gevent.subprocess，如果不可用则使用标准 subprocess
from gevent import spawn, subprocess

from bleak import BleakClient, BleakScanner
from bleak.backends.scanner import AdvertisementData


class BluetoothDevice:
    """蓝牙设备类"""

    def __init__(self, address: str, name: str = "", rssi: int = 0, metadata: dict = None):
        self.address = address
        self.name = name or address
        self.rssi = rssi
        self.metadata = metadata or {}
        self.connected = False
        self.client: Optional[BleakClient] = None

    def to_dict(self):
        """转换为字典，确保所有数据都是 JSON 可序列化的"""
        return {
            "address": str(self.address),
            "name": str(self.name) if self.name else str(self.address),
            "rssi": int(self.rssi) if self.rssi else 0,
            "connected": bool(self.connected),
            "metadata": self._ensure_json_serializable(self.metadata)
        }

    def _ensure_json_serializable(self, obj):
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


class BluetoothMgr:
    def _extract_metadata(self, advertisement_data) -> Dict:
        if not advertisement_data:
            return {}
        metadata: Dict[str, Any] = {}

        manufacturer_data = getattr(advertisement_data, "manufacturer_data", None) or {}
        if manufacturer_data:
            metadata["manufacturer_data"] = {
                str(k): {
                    "hex": v.hex(),
                    "length": len(v)
                } if isinstance(v, bytes) else v
                for k, v in manufacturer_data.items()
            }

        service_data = getattr(advertisement_data, "service_data", None) or {}
        if service_data:
            metadata["service_data"] = {
                str(k): {
                    "hex": v.hex(),
                    "length": len(v)
                } if isinstance(v, bytes) else v
                for k, v in service_data.items()
            }

        service_uuids = getattr(advertisement_data, "service_uuids", None)
        if service_uuids:
            metadata["service_uuids"] = [str(uuid) for uuid in service_uuids]

        local_name = getattr(advertisement_data, "local_name", None)
        if local_name:
            metadata["local_name"] = local_name

        tx_power = getattr(advertisement_data, "tx_power", None)
        if tx_power is not None:
            metadata["tx_power"] = tx_power

        return metadata

    """蓝牙设备管理器"""

    def __init__(self):
        log.info("[BLUETOOTH] BluetoothMgr init")
        self.devices: Dict[str, BluetoothDevice] = {}  # address -> BluetoothDevice
        self.scanning = False
        self._scan_task = None

    async def scan_devices(self, timeout: float = 5.0) -> List[Dict]:
        if self.scanning:
            log.warning("[BLUETOOTH] Already scanning")
            return []

        try:
            self.scanning = True
            log.info(f"[BLUETOOTH] Starting scan (timeout: {timeout}s)")

            # 使用 return_adv=True 获取设备和广告数据
            devices_dict = await BleakScanner.discover(timeout=timeout, return_adv=True)
            device_list = []

            for device, advertisement_data in devices_dict.values():
                # 从 AdvertisementData 获取 rssi
                rssi = getattr(advertisement_data, "rssi", 0) or 0

                # 获取友好名称：优先使用 local_name，其次使用 device.name
                # 如果都没有，使用 "Unknown Device" + 地址后6位
                friendly_name = None
                if advertisement_data and hasattr(advertisement_data, 'local_name') and advertisement_data.local_name:
                    friendly_name = advertisement_data.local_name
                elif device.name:
                    friendly_name = device.name
                else:
                    # 使用地址的后6位作为标识
                    addr_short = device.address.replace(
                        '-', '')[-6:].upper() if '-' in device.address else device.address[-6:].upper()
                    friendly_name = f"Unknown Device ({addr_short})"

                # 构建 metadata（从 advertisement_data 中提取）
                metadata = self._extract_metadata(advertisement_data)

                device_info = {"address": device.address, "name": friendly_name, "rssi": rssi, "metadata": metadata}
                device_list.append(device_info)

                # 更新设备列表
                if device.address not in self.devices:
                    self.devices[device.address] = BluetoothDevice(address=device.address,
                                                                   name=friendly_name,
                                                                   rssi=rssi,
                                                                   metadata=metadata)
                else:
                    # 更新现有设备信息
                    self.devices[device.address].name = friendly_name
                    self.devices[device.address].rssi = rssi
                    self.devices[device.address].metadata = metadata

            log.info(f"[BLUETOOTH] Found {len(device_list)} devices")
            return device_list

        except Exception as e:
            log.error(f"[BLUETOOTH] Scan error: {e}")
            return []
        finally:
            self.scanning = False

    async def _get_device_name_from_gatt(self, client: BleakClient) -> Optional[str]:
        """
        尝试从 GATT 服务读取设备名称
        :param client: 已连接的 BleakClient
        :return: 设备名称，如果无法获取则返回 None
        """
        try:
            # 设备名称特征 UUID: 0x2A00
            device_name_uuid = "00002a00-0000-1000-8000-00805f9b34fb"
            name_bytes = await client.read_gatt_char(device_name_uuid)
            if name_bytes:
                # 尝试 UTF-8 解码
                try:
                    return name_bytes.decode('utf-8').strip('\x00')
                except UnicodeDecodeError:
                    # 尝试其他编码
                    try:
                        return name_bytes.decode('gbk').strip('\x00')
                    except UnicodeDecodeError:
                        return None
        except Exception as e:
            log.debug(f"[BLUETOOTH] Could not read device name from GATT: {e}")
            return None

    async def connect_device(self, address: str, fetch_name: bool = True) -> Dict:

        try:
            if address in self.devices and self.devices[address].connected:
                return {"code": 0, "msg": "Already connected", "data": self.devices[address].to_dict()}

            log.info(f"[BLUETOOTH] Connecting to device: {address}")
            client = BleakClient(address)
            await client.connect()

            if address not in self.devices:
                self.devices[address] = BluetoothDevice(address=address)

            device = self.devices[address]
            device.client = client
            device.connected = True

            # 尝试从 GATT 获取设备名称
            if fetch_name and (not device.name or device.name == address):
                gatt_name = await self._get_device_name_from_gatt(client)
                if gatt_name:
                    device.name = gatt_name
                    log.info(f"[BLUETOOTH] Got device name from GATT: {gatt_name}")

            log.info(f"[BLUETOOTH] Connected to device: {address}")
            return {"code": 0, "msg": "Connected", "data": device.to_dict()}

        except Exception as e:
            log.error(f"[BLUETOOTH] Connect error: {e}")
            return {"code": -1, "msg": f"Connection failed: {str(e)}"}

    async def disconnect_device(self, address: str) -> Dict:

        try:
            if address not in self.devices:
                return {"code": -1, "msg": "Device not found"}

            device = self.devices[address]
            if not device.connected or device.client is None:
                return {"code": 0, "msg": "Already disconnected"}

            log.info(f"[BLUETOOTH] Disconnecting device: {address}")
            await device.client.disconnect()
            device.connected = False
            device.client = None

            log.info(f"[BLUETOOTH] Disconnected device: {address}")
            return {"code": 0, "msg": "Disconnected", "data": device.to_dict()}

        except Exception as e:
            log.error(f"[BLUETOOTH] Disconnect error: {e}")
            return {"code": -1, "msg": f"Disconnect failed: {str(e)}"}

    def get_device_list(self) -> List[Dict]:
        return [device.to_dict() for device in self.devices.values()]

    def get_device(self, address: str) -> Optional[Dict]:
        if address in self.devices:
            return self.devices[address].to_dict()
        return None

    def _find_command(self, cmd_name):
        # 首先尝试使用 shutil.which
        cmd_path = shutil.which(cmd_name)
        if cmd_path:
            return cmd_path

        # 如果找不到，尝试常见路径
        common_paths = [
            "/usr/bin",
            "/usr/local/bin",
            "/bin",
            "/sbin",
            "/usr/sbin",
        ]
        for path in common_paths:
            full_path = os.path.join(path, cmd_name)
            if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                return full_path

        return None

    def _run_subprocess_safe(self, cmd, timeout=10, env=None):

        def _run():
            try:
                # 如果是字符串命令，尝试查找完整路径
                if isinstance(cmd, list) and len(cmd) > 0:
                    cmd_name = cmd[0]
                    cmd_path = self._find_command(cmd_name)
                    if cmd_path:
                        cmd[0] = cmd_path

                # 设置环境变量，确保包含系统 PATH
                process_env = os.environ.copy()
                if env:
                    process_env.update(env)
                # 确保 PATH 包含常见路径
                if 'PATH' not in process_env or not process_env['PATH']:
                    process_env['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
                else:
                    # 确保常见路径在 PATH 中
                    common_paths = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
                    if common_paths not in process_env['PATH']:
                        process_env['PATH'] = f"{process_env['PATH']}:{common_paths}"

                process = subprocess.Popen(cmd,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           text=True,
                                           env=process_env)
                stdout, stderr = process.communicate(timeout=timeout)
                return process.returncode, stdout, stderr
            except FileNotFoundError as e:
                # 命令不存在
                log.warning(f"[BLUETOOTH] Command not found: {cmd[0] if isinstance(cmd, list) else cmd}")
                return -2, "", str(e)
            except Exception as e:
                log.error(f"[BLUETOOTH] Subprocess error: {e}")
                return -1, "", str(e)

        # 在独立的 greenlet 中运行，避免线程问题
        greenlet = spawn(_run)
        return greenlet.get(timeout=timeout + 2)

    def get_system_paired_devices(self) -> List[Dict]:
        results: List[Dict] = []

        try:
            # 使用 bluetoothctl 获取已配对设备
            result_code, stdout, _ = self._run_subprocess_safe(["bluetoothctl", "devices", "Paired"], timeout=10)
            paired_devices: Dict[str, str] = {}
            if result_code == 0:
                for line in stdout.strip().split('\n'):
                    if line.strip() and line.startswith('Device'):
                        parts = line.split(' ', 2)
                        if len(parts) >= 2:
                            address = parts[1]
                            name = parts[2] if len(parts) > 2 else address
                            paired_devices[address] = name

            # 获取已连接设备
            connected_addresses: set[str] = set()
            result_code, stdout, _ = self._run_subprocess_safe(["bluetoothctl", "devices", "Connected"], timeout=10)
            if result_code == 0:
                for line in stdout.strip().split('\n'):
                    if line.strip() and line.startswith('Device'):
                        parts = line.split(' ', 2)
                        if len(parts) >= 2:
                            connected_addresses.add(parts[1])

            for address, name in paired_devices.items():
                results.append({
                    "address": address,
                    "name": name,
                    "connected": address in connected_addresses
                })

            log.info(f"[BLUETOOTH] Found {len(results)} system paired devices")
            return results

        except FileNotFoundError:
            log.warning("[BLUETOOTH] bluetoothctl not found")
            return []
        except Exception as e:
            log.error(f"[BLUETOOTH] Error getting system paired devices: {e}")
            return []

# 全局实例
_bluetooth_mgr: Optional[BluetoothMgr] = None


def get_bluetooth_mgr() -> BluetoothMgr:
    """获取蓝牙管理器实例"""
    global _bluetooth_mgr
    if _bluetooth_mgr is None:
        _bluetooth_mgr = BluetoothMgr()
    return _bluetooth_mgr


# 同步包装函数（用于在Flask路由中使用）
def scan_devices_sync(timeout: float = 5.0) -> List[Dict]:
    """同步扫描设备"""
    try:
        return run_async(get_bluetooth_mgr().scan_devices(timeout), timeout=timeout + 2.0)
    except asyncio.TimeoutError:
        log.error(f"[BLUETOOTH] Scan timeout after {timeout + 2.0}s")
        return []
    except Exception as e:
        log.error(f"[BLUETOOTH] Scan error: {e}")
        return []


def get_system_paired_devices_sync() -> List[Dict]:
    """
    同步获取系统已配对的蓝牙设备列表
    :return: 已配对设备列表
    """
    try:
        return get_bluetooth_mgr().get_system_paired_devices()
    except Exception as e:
        log.error(f"[BLUETOOTH] Get system paired devices error: {e}")
        return []


def connect_device_sync(address: str, timeout: float = 10.0) -> Dict:
    """同步连接设备"""
    try:
        return run_async(get_bluetooth_mgr().connect_device(address), timeout=timeout)
    except asyncio.TimeoutError:
        log.error(f"[BLUETOOTH] Connect timeout after {timeout}s")
        return {"code": -1, "msg": f"Connection timeout after {timeout}s"}
    except Exception as e:
        log.error(f"[BLUETOOTH] Connect error: {e}")
        return {"code": -1, "msg": f"Connection failed: {str(e)}"}


def disconnect_device_sync(address: str, timeout: float = 5.0) -> Dict:
    """同步断开设备"""
    try:
        return run_async(get_bluetooth_mgr().disconnect_device(address), timeout=timeout)
    except asyncio.TimeoutError:
        log.error(f"[BLUETOOTH] Disconnect timeout after {timeout}s")
        return {"code": -1, "msg": f"Disconnect timeout after {timeout}s"}
    except Exception as e:
        log.error(f"[BLUETOOTH] Disconnect error: {e}")
        return {"code": -1, "msg": f"Disconnect failed: {str(e)}"}


# _run_async 已移至 core.__init__.py 作为 run_async

if __name__ == "__main__":
    # 测试代码
    print("Bluetooth Manager Test")
    # 测试扫描
    devices = scan_devices_sync(timeout=3.0)
    print(f"Found {len(devices)} devices")
    for device in devices:
        print(f"【{device['address']}】{device['name']}")
    # 测试获取系统已连接的设备
    connected_devices = get_system_paired_devices_sync()
    print(f"Found {len(connected_devices)} connected devices")
    for device in connected_devices:
        print(f"【{device.get('address', 'N/A')}】{device.get('name', 'Unknown')}")
