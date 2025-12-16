'''
蓝牙设备管理
'''
import os
import shutil
from typing import Any, Dict, List, Optional

from gevent import spawn, subprocess
from bleak import BleakClient, BleakScanner

from core.async_util import run_async
from core.log_config import root_logger

log = root_logger()

# 常量
DEVICE_NAME_UUID = "00002a00-0000-1000-8000-00805f9b34fb"
COMMON_PATHS = [
    "/usr/bin",
    "/usr/local/bin",
    "/bin",
    "/sbin",
    "/usr/sbin",
]
DEFAULT_PATH = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'


def _is_timeout_error(error: Exception) -> bool:
    """检查是否为超时错误"""
    error_msg = str(error).lower()
    return "timeout" in error_msg or "timed out" in error_msg


class BluetoothDev:
    """蓝牙设备类"""

    def __init__(self, address: str, name: str = "", rssi: int = 0, metadata: dict = None):
        self.address = address
        self.name = name or address
        self.rssi = rssi
        self.metadata = metadata or {}
        self.connected = False
        self.client: Optional[BleakClient] = None

    def to_dict(self) -> Dict:
        """转换为字典，确保所有数据都是 JSON 可序列化的"""
        return {
            "address": str(self.address),
            "name": str(self.name) if self.name else str(self.address),
            "rssi": int(self.rssi) if self.rssi else 0,
            "connected": bool(self.connected),
            "metadata": self._ensure_json_serializable(self.metadata)
        }

    def _ensure_json_serializable(self, obj):
        """确保对象可 JSON 序列化"""
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
    """蓝牙设备管理器"""

    def __init__(self):
        log.info("[BLUETOOTH] BluetoothMgr init")
        self.devices: Dict[str, BluetoothDev] = {}
        self.scanning = False

    def _extract_metadata(self, advertisement_data) -> Dict:
        """从广告数据中提取元数据"""
        if not advertisement_data:
            return {}
        
        metadata: Dict[str, Any] = {}
        
        # 提取制造商数据
        manufacturer_data = getattr(advertisement_data, "manufacturer_data", None) or {}
        if manufacturer_data:
            metadata["manufacturer_data"] = {
                str(k): {"hex": v.hex(), "length": len(v)} if isinstance(v, bytes) else v
                for k, v in manufacturer_data.items()
            }
        
        # 提取服务数据
        service_data = getattr(advertisement_data, "service_data", None) or {}
        if service_data:
            metadata["service_data"] = {
                str(k): {"hex": v.hex(), "length": len(v)} if isinstance(v, bytes) else v
                for k, v in service_data.items()
            }
        
        # 提取服务 UUID
        service_uuids = getattr(advertisement_data, "service_uuids", None)
        if service_uuids:
            metadata["service_uuids"] = [str(uuid) for uuid in service_uuids]
        
        # 提取本地名称
        local_name = getattr(advertisement_data, "local_name", None)
        if local_name:
            metadata["local_name"] = local_name
        
        # 提取发射功率
        tx_power = getattr(advertisement_data, "tx_power", None)
        if tx_power is not None:
            metadata["tx_power"] = tx_power
        
        return metadata

    def _get_friendly_name(self, device, advertisement_data) -> str:
        """获取设备友好名称"""
        if advertisement_data and hasattr(advertisement_data, 'local_name') and advertisement_data.local_name:
            return advertisement_data.local_name
        elif device.name:
            return device.name
        else:
            # 使用地址的后6位作为标识
            addr_short = device.address.replace('-', '')[-6:].upper() if '-' in device.address else device.address[-6:].upper()
            return f"Unknown Device ({addr_short})"

    async def scan_devices(self, timeout: float = 5.0) -> List[Dict]:
        """扫描蓝牙设备"""
        if self.scanning:
            log.warning("[BLUETOOTH] Already scanning")
            return []

        try:
            self.scanning = True
            log.info(f"[BLUETOOTH] Starting scan (timeout: {timeout}s)")

            devices_dict = await BleakScanner.discover(timeout=timeout, return_adv=True)
            device_list = []

            for device, advertisement_data in devices_dict.values():
                rssi = getattr(advertisement_data, "rssi", 0) or 0
                friendly_name = self._get_friendly_name(device, advertisement_data)
                metadata = self._extract_metadata(advertisement_data)

                device_info = {
                    "address": device.address,
                    "name": friendly_name,
                    "rssi": rssi,
                    "metadata": metadata
                }
                device_list.append(device_info)

                # 更新设备列表
                if device.address not in self.devices:
                    self.devices[device.address] = BluetoothDev(
                        address=device.address,
                        name=friendly_name,
                        rssi=rssi,
                        metadata=metadata
                    )
                else:
                    # 更新现有设备信息
                    existing_device = self.devices[device.address]
                    existing_device.name = friendly_name
                    existing_device.rssi = rssi
                    existing_device.metadata = metadata

            log.info(f"[BLUETOOTH] Found {len(device_list)} devices")
            return device_list

        except Exception as e:
            log.error(f"[BLUETOOTH] Scan error: {e}")
            return []
        finally:
            self.scanning = False

    async def _get_device_name_from_gatt(self, client: BleakClient) -> Optional[str]:
        """尝试从 GATT 服务读取设备名称"""
        try:
            name_bytes = await client.read_gatt_char(DEVICE_NAME_UUID)
            if not name_bytes:
                return None
            
            # 尝试 UTF-8 解码
            try:
                return name_bytes.decode('utf-8').strip('\x00')
            except UnicodeDecodeError:
                # 尝试 GBK 解码
                try:
                    return name_bytes.decode('gbk').strip('\x00')
                except UnicodeDecodeError:
                    return None
        except Exception as e:
            log.debug(f"[BLUETOOTH] Could not read device name from GATT: {e}")
            return None

    async def connect_device(self, address: str, fetch_name: bool = True) -> Dict:
        """连接蓝牙设备"""
        try:
            if address in self.devices and self.devices[address].connected:
                return {"code": 0, "msg": "Already connected", "data": self.devices[address].to_dict()}

            log.info(f"[BLUETOOTH] Connecting to device: {address}")
            client = BleakClient(address)
            await client.connect()

            if address not in self.devices:
                self.devices[address] = BluetoothDev(address=address)

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
        """断开蓝牙设备"""
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
        """获取所有设备列表"""
        return [device.to_dict() for device in self.devices.values()]

    def get_device(self, address: str) -> Optional[Dict]:
        """获取指定设备"""
        if address in self.devices:
            return self.devices[address].to_dict()
        return None

    def _find_command(self, cmd_name: str) -> Optional[str]:
        """查找命令的完整路径"""
        cmd_path = shutil.which(cmd_name)
        if cmd_path:
            return cmd_path

        for path in COMMON_PATHS:
            full_path = os.path.join(path, cmd_name)
            if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                return full_path

        return None

    def _run_subprocess_safe(self, cmd, timeout=10, env=None):
        """安全地运行子进程"""
        def _run():
            try:
                # 查找命令完整路径
                if isinstance(cmd, list) and len(cmd) > 0:
                    cmd_path = self._find_command(cmd[0])
                    if cmd_path:
                        cmd[0] = cmd_path

                # 设置环境变量
                process_env = os.environ.copy()
                if env:
                    process_env.update(env)
                
                # 确保 PATH 包含常见路径
                if 'PATH' not in process_env or not process_env['PATH']:
                    process_env['PATH'] = DEFAULT_PATH
                elif DEFAULT_PATH not in process_env['PATH']:
                    process_env['PATH'] = f"{process_env['PATH']}:{DEFAULT_PATH}"

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=process_env
                )
                stdout, stderr = process.communicate(timeout=timeout)
                return process.returncode, stdout, stderr
            except FileNotFoundError as e:
                log.warning(f"[BLUETOOTH] Command not found: {cmd[0] if isinstance(cmd, list) else cmd}")
                return -2, "", str(e)
            except Exception as e:
                log.error(f"[BLUETOOTH] Subprocess error: {e}")
                return -1, "", str(e)

        greenlet = spawn(_run)
        return greenlet.get(timeout=timeout + 2)

    def _parse_bluetoothctl_output(self, stdout: str) -> Dict[str, str]:
        """解析 bluetoothctl 输出"""
        devices: Dict[str, str] = {}
        for line in stdout.strip().split('\n'):
            if line.strip() and line.startswith('Device'):
                parts = line.split(' ', 2)
                if len(parts) >= 2:
                    address = parts[1]
                    name = parts[2] if len(parts) > 2 else address
                    devices[address] = name
        return devices

    def get_system_paired_devices(self) -> List[Dict]:
        """获取系统已配对的蓝牙设备"""
        try:
            # 获取已配对设备
            result_code, stdout, _ = self._run_subprocess_safe(["bluetoothctl", "devices", "Paired"], timeout=10)
            paired_devices = {}
            if result_code == 0:
                paired_devices = self._parse_bluetoothctl_output(stdout)

            # 获取已连接设备
            connected_addresses = set()
            result_code, stdout, _ = self._run_subprocess_safe(["bluetoothctl", "devices", "Connected"], timeout=10)
            if result_code == 0:
                connected_devices = self._parse_bluetoothctl_output(stdout)
                connected_addresses = set(connected_devices.keys())

            # 构建结果列表
            results = [
                {
                    "address": address,
                    "name": name,
                    "connected": address in connected_addresses
                }
                for address, name in paired_devices.items()
            ]

            log.info(f"[BLUETOOTH] Found {len(results)} system paired devices")
            return results

        except FileNotFoundError:
            log.warning("[BLUETOOTH] bluetoothctl not found")
            return []
        except Exception as e:
            log.error(f"[BLUETOOTH] Error getting system paired devices: {e}")
            return []


# 全局实例
bluetooth_mgr: Optional[BluetoothMgr] = BluetoothMgr()


def scan_devices_sync(timeout: float = 5.0) -> List[Dict]:
    """同步扫描设备（gevent 环境友好）"""
    try:
        return run_async(bluetooth_mgr.scan_devices(timeout), timeout=timeout + 2.0)
    except Exception as e:
        if _is_timeout_error(e):
            log.error(f"[BLUETOOTH] Scan timeout after {timeout + 2.0}s")
        else:
            log.error(f"[BLUETOOTH] Scan error: {e}")
        return []


def get_system_paired_devices_sync() -> List[Dict]:
    """同步获取系统已配对的蓝牙设备列表"""
    try:
        return bluetooth_mgr.get_system_paired_devices()
    except Exception as e:
        log.error(f"[BLUETOOTH] Get system paired devices error: {e}")
        return []


def connect_device_sync(address: str, timeout: float = 10.0) -> Dict:
    """同步连接设备"""
    try:
        return run_async(bluetooth_mgr.connect_device(address), timeout=timeout)
    except Exception as e:
        if _is_timeout_error(e):
            log.error(f"[BLUETOOTH] Connect timeout after {timeout}s")
            return {"code": -1, "msg": f"Connection timeout after {timeout}s"}
        else:
            log.error(f"[BLUETOOTH] Connect error: {e}")
            return {"code": -1, "msg": f"Connection failed: {str(e)}"}


def disconnect_device_sync(address: str, timeout: float = 5.0) -> Dict:
    """同步断开设备"""
    try:
        return run_async(bluetooth_mgr.disconnect_device(address), timeout=timeout)
    except Exception as e:
        if _is_timeout_error(e):
            log.error(f"[BLUETOOTH] Disconnect timeout after {timeout}s")
            return {"code": -1, "msg": f"Disconnect timeout after {timeout}s"}
        else:
            log.error(f"[BLUETOOTH] Disconnect error: {e}")
            return {"code": -1, "msg": f"Disconnect failed: {str(e)}"}


if __name__ == "__main__":
    # 测试代码
    print("Bluetooth Manager Test")
    devices = scan_devices_sync(timeout=3.0)
    print(f"Found {len(devices)} devices")
    for device in devices:
        print(f"【{device['address']}】{device['name']}")
    
    connected_devices = get_system_paired_devices_sync()
    print(f"Found {len(connected_devices)} connected devices")
    for device in connected_devices:
        print(f"【{device.get('address', 'N/A')}】{device.get('name', 'Unknown')}")
