"""
蓝牙设备管理器
"""
import asyncio
import os
import shutil
from typing import Any, Dict, List, Optional

from gevent import spawn, subprocess
from bleak import BleakClient, BleakScanner
from bleak.backends.scanner import AdvertisementData

from core.device.bluetooth import BluetoothDev
from core.tools.async_util import run_async
from core.log_config import app_logger

log = app_logger

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
PRINTABLE_RATIO_THRESHOLD = 0.7  # 可打印字符比例阈值


class BluetoothMgr:
    """蓝牙设备管理器"""

    def __init__(self):
        log.info("[BLUETOOTH] BluetoothMgr init")
        self.devices: Dict[str, BluetoothDev] = {}  # address -> BluetoothDev
        self.scanning = False
        self._scan_task = None

    def _update_or_create_device(self, address: str, name: str, metadata: Dict[str, Any]) -> BluetoothDev:
        """
        更新或创建设备对象
        :param address: 设备地址
        :param name: 设备名称
        :param metadata: 设备元数据
        :return: BluetoothDev 对象
        """
        address_upper = address.upper()
        if address_upper not in self.devices:
            self.devices[address_upper] = BluetoothDev(address=address_upper, name=name, metadata=metadata)
        else:
            # 更新现有设备信息
            self.devices[address_upper].name = name
            self.devices[address_upper].metadata = metadata
        return self.devices[address_upper]

    def _build_ble_metadata(self, advertisement_data: Optional[AdvertisementData]) -> Dict[str, Any]:
        """
        从 BLE 广告数据构建 metadata
        :param advertisement_data: BLE 广告数据
        :return: metadata 字典
        """
        metadata = {}
        if not advertisement_data:
            return metadata

        # 处理 manufacturer_data
        if hasattr(advertisement_data, 'manufacturer_data') and advertisement_data.manufacturer_data:
            manufacturer_data_decoded = {}
            for manufacturer_id, data_bytes in advertisement_data.manufacturer_data.items():
                if isinstance(data_bytes, bytes):
                    # 只尝试解码可能包含文本的部分（检查是否大部分是可打印字符）
                    decoded_str = None
                    # 先检查是否大部分字节在可打印 ASCII 范围内（0x20-0x7E）
                    printable_count = sum(1 for b in data_bytes if 0x20 <= b <= 0x7E)
                    ratio = printable_count / len(data_bytes) if len(data_bytes) > 0 else 0

                    # 如果超过阈值是可打印 ASCII，尝试解码
                    if ratio > PRINTABLE_RATIO_THRESHOLD:
                        for encoding in ['utf-8', 'gbk', 'gb2312']:
                            try:
                                test_str = data_bytes.decode(encoding)
                                # 检查是否包含中文字符或大部分是可打印字符
                                if any('\u4e00' <= c <= '\u9fff' for c in test_str) or \
                                   all(c.isprintable() or c.isspace() for c in test_str):
                                    decoded_str = test_str
                                    break
                            except (UnicodeDecodeError, UnicodeError):
                                continue

                    # 构建返回数据
                    result = {'hex': data_bytes.hex(), 'length': len(data_bytes)}
                    if decoded_str:
                        result['decoded'] = decoded_str
                    manufacturer_data_decoded[manufacturer_id] = result
                else:
                    # 如果不是 bytes，直接使用；如果是 bytes，转换为可序列化格式
                    if isinstance(data_bytes, bytes):
                        manufacturer_data_decoded[manufacturer_id] = {
                            'hex': data_bytes.hex(),
                            'length': len(data_bytes)
                        }
                    else:
                        manufacturer_data_decoded[manufacturer_id] = data_bytes
            metadata['manufacturer_data'] = manufacturer_data_decoded

        # 处理 service_data
        if hasattr(advertisement_data, 'service_data'):
            if advertisement_data.service_data:
                service_data_dict = {}
                for service_uuid, data in advertisement_data.service_data.items():
                    if isinstance(data, bytes):
                        service_data_dict[str(service_uuid)] = {'hex': data.hex(), 'length': len(data)}
                    else:
                        service_data_dict[str(service_uuid)] = data
                metadata['service_data'] = service_data_dict
            else:
                metadata['service_data'] = {}

        # 处理 service_uuids
        if hasattr(advertisement_data, 'service_uuids'):
            if advertisement_data.service_uuids:
                metadata['service_uuids'] = [str(uuid) for uuid in advertisement_data.service_uuids]
            else:
                metadata['service_uuids'] = []

        # 处理其他字段
        if hasattr(advertisement_data, 'local_name'):
            metadata['local_name'] = advertisement_data.local_name
        if hasattr(advertisement_data, 'tx_power'):
            metadata['tx_power'] = advertisement_data.tx_power

        return metadata

    def _extract_metadata(self, advertisement_data) -> Dict:
        """从广告数据中提取元数据"""
        if not advertisement_data:
            return {}

        metadata: Dict[str, Any] = {}

        # 提取制造商数据
        manufacturer_data = getattr(advertisement_data, "manufacturer_data", None) or {}
        if manufacturer_data:
            metadata["manufacturer_data"] = {
                str(k): {
                    "hex": v.hex(),
                    "length": len(v)
                } if isinstance(v, bytes) else v
                for k, v in manufacturer_data.items()
            }

        # 提取服务数据
        service_data = getattr(advertisement_data, "service_data", None) or {}
        if service_data:
            metadata["service_data"] = {
                str(k): {
                    "hex": v.hex(),
                    "length": len(v)
                } if isinstance(v, bytes) else v
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

    def _get_friendly_name(self, device, advertisement_data: Optional[AdvertisementData] = None) -> str:
        """
        获取设备的友好名称
        :param device: BLE 设备对象
        :param advertisement_data: 广告数据
        :return: 友好名称
        """
        if advertisement_data and hasattr(advertisement_data, 'local_name') and advertisement_data.local_name:
            return advertisement_data.local_name
        elif device.name:
            return device.name
        else:
            # 使用地址的后6位作为标识
            addr_short = device.address.replace(
                '-', '')[-6:].upper() if '-' in device.address else device.address[-6:].upper()
            return f"Unknown Device ({addr_short})"

    async def scan_ble_devices(self, timeout: float = 5.0) -> List[Dict]:
        """扫描 BLE 蓝牙设备（使用 BleakScanner）"""
        if self.scanning:
            log.warning("[BLUETOOTH] Already scanning")
            return []

        try:
            self.scanning = True
            log.info(f"[BLUETOOTH] Starting BLE scan (timeout: {timeout}s)")

            # 使用 return_adv=True 获取设备和广告数据
            devices_dict = await BleakScanner.discover(timeout=timeout, return_adv=True)
            device_list = []

            for device, advertisement_data in devices_dict.values():
                friendly_name = self._get_friendly_name(device, advertisement_data)
                metadata = self._build_ble_metadata(advertisement_data)
                device_info = {"address": device.address, "name": friendly_name, "metadata": metadata}
                device_list.append(device_info)
                self._update_or_create_device(address=device.address, name=friendly_name, metadata=metadata)

            log.info(f"[BLUETOOTH] Found {len(device_list)} BLE devices")
            return device_list

        except Exception as e:
            log.error(f"[BLUETOOTH] BLE scan error: {e}")
            return []
        finally:
            self.scanning = False

    async def scan_devices(self, timeout: float = 5.0) -> List[Dict]:
        """扫描蓝牙设备（兼容性方法，实际调用 scan_ble_devices）"""
        return await self.scan_ble_devices(timeout)

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
            address_upper = address.upper()
            if address_upper in self.devices and self.devices[address_upper].connected:
                return {"code": 0, "msg": "Already connected", "data": self.devices[address_upper].to_dict()}

            log.info(f"[BLUETOOTH] Connecting to device: {address_upper}")
            client = BleakClient(address_upper)
            await client.connect()

            if address_upper not in self.devices:
                self.devices[address_upper] = BluetoothDev(address=address_upper)

            device = self.devices[address_upper]
            device.client = client
            device.connected = True

            # 尝试从 GATT 获取设备名称
            if fetch_name and (not device.name or device.name == address_upper):
                gatt_name = await self._get_device_name_from_gatt(client)
                if gatt_name:
                    device.name = gatt_name
                    log.info(f"[BLUETOOTH] Got device name from GATT: {gatt_name}")

            log.info(f"[BLUETOOTH] Connected to device: {address_upper}")
            return {"code": 0, "msg": "Connected", "data": device.to_dict()}

        except Exception as e:
            log.error(f"[BLUETOOTH] Connect error: {e}")
            if address.upper() in self.devices:
                self.devices[address.upper()].connected = False
            return {"code": -1, "msg": f"Connection failed: {str(e)}"}

    async def disconnect_device(self, address: str) -> Dict:
        """断开蓝牙设备"""
        try:
            address_upper = address.upper()
            if address_upper not in self.devices:
                return {"code": -1, "msg": "Device not found"}

            device = self.devices[address_upper]
            if not device.connected or device.client is None:
                return {"code": 0, "msg": "Already disconnected"}

            log.info(f"[BLUETOOTH] Disconnecting device: {address_upper}")
            await device.client.disconnect()
            device.connected = False
            device.client = None

            log.info(f"[BLUETOOTH] Disconnected device: {address_upper}")
            return {"code": 0, "msg": "Disconnected", "data": device.to_dict()}

        except Exception as e:
            log.error(f"[BLUETOOTH] Disconnect error: {e}")
            if address.upper() in self.devices:
                self.devices[address.upper()].connected = False
            return {"code": -1, "msg": f"Disconnect failed: {str(e)}"}

    def get_device_list(self) -> List[Dict]:
        """获取所有设备列表"""
        return [device.to_dict() for device in self.devices.values()]

    def get_device(self, address: str) -> Optional[Dict]:
        """获取指定设备"""
        address_upper = address.upper()
        if address_upper in self.devices:
            return self.devices[address_upper].to_dict()
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

                process = subprocess.Popen(cmd,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           text=True,
                                           env=process_env)
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

    def get_paired_devices(self, adapter: str = None) -> List[Dict]:
        """获取系统已配对的蓝牙设备列表"""
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
            results = [{
                "address": address,
                "name": name,
                "connected": address in connected_addresses
            } for address, name in paired_devices.items()]

            log.info(f"[BLUETOOTH] Found {len(results)} paired devices")
            return results

        except FileNotFoundError:
            log.warning("[BLUETOOTH] bluetoothctl not found")
            return []
        except Exception as e:
            log.error(f"[BLUETOOTH] Error getting paired devices: {e}")
            return []

    def scan_devices_sync(self, timeout: float = 5.0) -> List[Dict]:
        """
        同步扫描传统蓝牙设备（在事件循环中运行）
        :param timeout: 扫描超时时间（秒）
        :return: 设备列表
        """
        try:
            return run_async(self.scan_devices(timeout), timeout=timeout + 2.0)
        except asyncio.TimeoutError:
            log.error(f"[BLUETOOTH] Scan timeout after {timeout}s")
            return []
        except Exception as e:
            log.error(f"[BLUETOOTH] Scan error: {e}")
            return []

    def scan_ble_devices_sync(self, timeout: float = 5.0) -> List[Dict]:
        """
        同步扫描 BLE 蓝牙设备（在事件循环中运行）
        :param timeout: 扫描超时时间（秒）
        :return: 设备列表
        """
        try:
            return run_async(self.scan_ble_devices(timeout), timeout=timeout + 2.0)
        except asyncio.TimeoutError:
            log.error(f"[BLUETOOTH] BLE scan timeout after {timeout}s")
            return []
        except Exception as e:
            log.error(f"[BLUETOOTH] BLE scan error: {e}")
            return []

    def connect_device_sync(self, address: str, timeout: float = 10.0) -> Dict:
        """同步连接设备"""
        try:
            return run_async(self.connect_device(address), timeout=timeout)
        except (asyncio.TimeoutError, Exception) as e:
            msg = f"Connection timeout after {timeout}s" if isinstance(
                e, asyncio.TimeoutError) else f"Connection failed: {str(e)}"
            log.error(f"[BLUETOOTH] Connect error: {e}")
            return {"code": -1, "msg": msg}

    def disconnect_device_sync(self, address: str, timeout: float = 5.0) -> Dict:
        """同步断开设备"""
        try:
            return run_async(self.disconnect_device(address), timeout=timeout)
        except (asyncio.TimeoutError, Exception) as e:
            msg = f"Disconnect timeout after {timeout}s" if isinstance(
                e, asyncio.TimeoutError) else f"Disconnect failed: {str(e)}"
            log.error(f"[BLUETOOTH] Disconnect error: {e}")
            return {"code": -1, "msg": msg}


# 全局实例
bluetooth_mgr = BluetoothMgr()
