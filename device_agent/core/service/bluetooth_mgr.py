'''
蓝牙设备管理 (Linux Only)
'''
import asyncio
import os
from typing import Dict, List, Optional

from core.log_config import root_logger
from core.utils import find_command, run_async, run_subprocess_safe

log = root_logger()

from bleak import BleakClient, BleakScanner
from bleak.backends.scanner import AdvertisementData

from core.device.bluetooth_dev import BluetoothDev


class BluetoothMgr:
    """蓝牙设备管理器"""

    def __init__(self):
        log.info("[BLUETOOTH] BluetoothMgr init")
        self.devices: Dict[str, BluetoothDev] = {}  # address -> BluetoothDev
        self.scanning = False
        self._scan_task = None

    async def scan_devices(self, timeout: float = 5.0) -> List[Dict]:
        """
        扫描蓝牙设备
        :param timeout: 扫描超时时间（秒）
        :return: 设备列表
        """

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
                metadata = {}
                if advertisement_data:
                    # 处理 manufacturer_data
                    # 注意：manufacturer_data 通常是二进制数据，不应该强制解码为文本
                    if hasattr(advertisement_data, 'manufacturer_data') and advertisement_data.manufacturer_data:
                        manufacturer_data_decoded = {}
                        for manufacturer_id, data_bytes in advertisement_data.manufacturer_data.items():
                            if isinstance(data_bytes, bytes):
                                # 只尝试解码可能包含文本的部分（检查是否大部分是可打印字符）
                                decoded_str = None
                                # 先检查是否大部分字节在可打印 ASCII 范围内（0x20-0x7E）或常见中文编码范围
                                printable_count = sum(1 for b in data_bytes if 0x20 <= b <= 0x7E)
                                ratio = printable_count / len(data_bytes) if len(data_bytes) > 0 else 0

                                # 如果超过 70% 是可打印 ASCII，尝试解码
                                if ratio > 0.7:
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

                    if hasattr(advertisement_data, 'service_data'):
                        if advertisement_data.service_data:
                            # 处理 service_data，确保所有 bytes 都被转换
                            service_data_dict = {}
                            for service_uuid, data in advertisement_data.service_data.items():
                                if isinstance(data, bytes):
                                    service_data_dict[str(service_uuid)] = {'hex': data.hex(), 'length': len(data)}
                                else:
                                    service_data_dict[str(service_uuid)] = data
                            metadata['service_data'] = service_data_dict
                        else:
                            metadata['service_data'] = {}

                    if hasattr(advertisement_data, 'service_uuids'):
                        if advertisement_data.service_uuids:
                            # 确保所有 UUID 都转换为字符串
                            metadata['service_uuids'] = [str(uuid) for uuid in advertisement_data.service_uuids]
                        else:
                            metadata['service_uuids'] = []
                    if hasattr(advertisement_data, 'local_name'):
                        metadata['local_name'] = advertisement_data.local_name
                    if hasattr(advertisement_data, 'tx_power'):
                        metadata['tx_power'] = advertisement_data.tx_power

                device_info = {"address": device.address, "name": friendly_name, "metadata": metadata}
                device_list.append(device_info)

                # 更新设备列表
                if device.address not in self.devices:
                    self.devices[device.address] = BluetoothDev(address=device.address,
                                                                name=friendly_name,
                                                                metadata=metadata)
                else:
                    # 更新现有设备信息
                    self.devices[device.address].name = friendly_name
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
        """
        连接蓝牙设备
        :param address: 设备地址
        :param fetch_name: 是否尝试从 GATT 获取设备名称
        :return: 连接结果
        """

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
        """
        断开蓝牙设备
        :param address: 设备地址
        :return: 断开结果
        """

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

    def get_system_paired_devices(self) -> List[Dict]:
        """
        获取系统已配对的蓝牙设备列表 (Linux Only)
        :return: 已配对设备列表
        """
        paired_devices_list = []

        try:
            # 使用 bluetoothctl 获取已配对设备，并检查连接状态
            try:
                # 先获取所有已配对设备
                result_code, stdout, stderr = run_subprocess_safe(["bluetoothctl", "devices", "Paired"],
                                                                  timeout=10, log_prefix="BLUETOOTH")
                if result_code == 0:
                    paired_devices = {}
                    # 解析 bluetoothctl 输出格式: "Device XX:XX:XX:XX:XX:XX Device Name"
                    for line in stdout.strip().split('\n'):
                        if line.strip() and line.startswith('Device'):
                            parts = line.split(' ', 2)
                            if len(parts) >= 2:
                                address = parts[1]
                                name = parts[2] if len(parts) > 2 else address
                                paired_devices[address] = name

                    # 对每个已配对设备使用 bluetoothctl info 查询连接状态
                    for address, name in paired_devices.items():
                        is_connected = False
                        try:
                            result_code, stdout, stderr = run_subprocess_safe(["bluetoothctl", "info", address],
                                                                              timeout=5, log_prefix="BLUETOOTH")
                            if result_code == 0:
                                # 解析输出，查找 "Connected: yes" 或 "Connected: no"
                                for line in stdout.split('\n'):
                                    line = line.strip()
                                    if line.startswith('Connected:'):
                                        # 格式: "Connected: yes" 或 "Connected: no"
                                        value = line.split(':', 1)[1].strip().lower()
                                        is_connected = (value == 'yes')
                                        break
                        except Exception as e:
                            log.debug(f"[BLUETOOTH] Failed to get info for {address}: {e}")

                        device_info = {
                            "address": address,
                            "name": name,
                            "connected": is_connected,
                        }
                        paired_devices_list.append(device_info)

            except FileNotFoundError:
                # 如果没有 bluetoothctl，尝试使用 hcitool
                log.warning("[BLUETOOTH] bluetoothctl not found, trying hcitool")
                try:
                    # hcitool con 只返回已连接的设备
                    result_code, stdout, stderr = run_subprocess_safe(["hcitool", "con"], timeout=10, log_prefix="BLUETOOTH")
                    if result_code == 0:
                        # 解析 hcitool 输出
                        for line in stdout.split('\n'):
                            if '>' in line:
                                parts = line.split()
                                if len(parts) >= 2:
                                    address = parts[1]
                                    device_info = {
                                        "address": address,
                                        "name": address,  # hcitool 不提供名称
                                        "connected": True,
                                    }
                                    paired_devices_list.append(device_info)
                except FileNotFoundError:
                    log.warning("[BLUETOOTH] hcitool not found either")

            log.info(f"[BLUETOOTH] Found {len(paired_devices_list)} system paired devices")
            return paired_devices_list

        except Exception as e:
            log.error(f"[BLUETOOTH] Error getting system paired devices: {e}")
            return []

    async def read_characteristic(self, address: str, characteristic_uuid: str) -> Dict:
        """
        读取特征值
        :param address: 设备地址
        :param characteristic_uuid: 特征UUID
        :return: 读取结果
        """

        try:
            if address not in self.devices or not self.devices[address].connected:
                return {"code": -1, "msg": "Device not connected"}

            device = self.devices[address]
            data = await device.client.read_gatt_char(characteristic_uuid)

            log.info(f"[BLUETOOTH] Read characteristic {characteristic_uuid} from {address}")
            return {"code": 0, "msg": "Read success", "data": data.hex()}

        except Exception as e:
            log.error(f"[BLUETOOTH] Read error: {e}")
            return {"code": -1, "msg": f"Read failed: {str(e)}"}

    async def write_characteristic(self, address: str, characteristic_uuid: str, data: bytes) -> Dict:
        """
        写入特征值
        :param address: 设备地址
        :param characteristic_uuid: 特征UUID
        :param data: 要写入的数据
        :return: 写入结果
        """

        try:
            if address not in self.devices or not self.devices[address].connected:
                return {"code": -1, "msg": "Device not connected"}

            device = self.devices[address]
            await device.client.write_gatt_char(characteristic_uuid, data)

            log.info(f"[BLUETOOTH] Write characteristic {characteristic_uuid} to {address}")
            return {"code": 0, "msg": "Write success"}

        except Exception as e:
            log.error(f"[BLUETOOTH] Write error: {e}")
            return {"code": -1, "msg": f"Write failed: {str(e)}"}

    def scan_devices_sync(self, timeout: float = 5.0) -> List[Dict]:
        """
        同步扫描设备（在事件循环中运行）
        :param timeout: 扫描超时时间（秒）
        :return: 设备列表
        """
        try:
            return run_async(self.scan_devices(timeout), timeout=timeout, log_prefix="BLUETOOTH")
        except asyncio.TimeoutError:
            log.error(f"[BLUETOOTH] Scan timeout after {timeout}s")
            return []
        except Exception as e:
            log.error(f"[BLUETOOTH] Scan error: {e}")
            return []

    def get_connected_devices(self) -> List[Dict]:
        """
        获取所有已连接的设备（包括通过 BluetoothMgr 连接的和系统级别连接的）
        :return: 已连接设备列表
        """
        # 获取通过 BluetoothMgr 连接的设备（使用大写地址作为键）
        mgr_connected = {}
        for address, device in self.devices.items():
            if device.connected:
                device_dict = device.to_dict()
                address_upper = device_dict.get('address', '').upper()
                mgr_connected[address_upper] = device_dict
        
        # 获取系统级别已连接的设备（从已配对设备中筛选）
        paired_devices = self.get_system_paired_devices()
        system_connected = [device for device in paired_devices if device.get('connected', False)]
        
        # 合并列表，优先使用 BluetoothMgr 中的设备信息（更详细）
        all_connected = []
        system_addresses = set()
        
        # 先添加系统连接的设备
        for device in system_connected:
            address = device.get('address', '').upper()
            system_addresses.add(address)
            if address in mgr_connected:
                # 如果也在 BluetoothMgr 中，使用更详细的信息
                all_connected.append(mgr_connected[address])
            else:
                all_connected.append(device)
        
        # 添加只在 BluetoothMgr 中连接的设备
        for address, device in mgr_connected.items():
            if address not in system_addresses:
                all_connected.append(device)
        
        log.info(f"[BLUETOOTH] Found {len(all_connected)} total connected devices")
        return all_connected

    def connect_device_sync(self, address: str, timeout: float = 10.0) -> Dict:
        """同步连接设备"""
        try:
            return run_async(self.connect_device(address), timeout=timeout, log_prefix="BLUETOOTH")
        except asyncio.TimeoutError:
            log.error(f"[BLUETOOTH] Connect timeout after {timeout}s")
            return {"code": -1, "msg": f"Connection timeout after {timeout}s"}
        except Exception as e:
            log.error(f"[BLUETOOTH] Connect error: {e}")
            return {"code": -1, "msg": f"Connection failed: {str(e)}"}

    def disconnect_device_sync(self, address: str, timeout: float = 5.0) -> Dict:
        """同步断开设备"""
        try:
            return run_async(self.disconnect_device(address), timeout=timeout, log_prefix="BLUETOOTH")
        except asyncio.TimeoutError:
            log.error(f"[BLUETOOTH] Disconnect timeout after {timeout}s")
            return {"code": -1, "msg": f"Disconnect timeout after {timeout}s"}
        except Exception as e:
            log.error(f"[BLUETOOTH] Disconnect error: {e}")
            return {"code": -1, "msg": f"Disconnect failed: {str(e)}"}

    def _find_target_device(self, device_address: Optional[str], paired_devices: List[Dict]) -> Optional[Dict]:
        """
        查找目标蓝牙设备
        :param device_address: 设备地址（可选）
        :param paired_devices: 已配对设备列表
        :return: 目标设备字典
        """
        if device_address:
            # 查找指定地址的设备
            addr_upper = device_address.upper()
            target_device = next(
                (d for d in paired_devices if d.get('address', '').upper() == addr_upper),
                None
            )
            if not target_device:
                log.warning(f"[BLUETOOTH] Bluetooth device not found: {device_address}")
                # 即使没找到设备信息，仍然尝试构造 ALSA 设备名
                return {'address': device_address, 'name': device_address, 'connected': False}
            return target_device
        else:
            # 使用第一个已连接的设备
            target_device = next((d for d in paired_devices if d.get('connected')), None)
            if not target_device:
                log.warning("[BLUETOOTH] No connected bluetooth devices found")
                # 如果没有已连接的，使用第一个已配对的
                target_device = paired_devices[0]
                log.info(f"[BLUETOOTH] Using first paired device: {target_device.get('name')}")
            return target_device

    def get_alsa_name(self, device_address: Optional[str] = None, hci_adapter: str = 'hci0') -> Optional[str]:
        """
        获取 ALSA 蓝牙音频设备名称（直接根据 MAC 地址构造）
        :param device_address: 蓝牙设备地址（可选）
        :param hci_adapter: HCI 适配器名称，默认为 hci0
        :return: ALSA 设备名称，例如 "bluealsa:HCI=hci0,DEV=XX:XX:XX:XX:XX:XX,PROFILE=a2dp"
        """
        try:
            paired_devices = self.get_system_paired_devices()
            if not paired_devices:
                log.warning("[BLUETOOTH] No paired bluetooth devices found")
                return None

            target_device = self._find_target_device(device_address, paired_devices)
            if not target_device:
                return None

            device_address = target_device.get('address')
            device_name = target_device.get('name', device_address)
            is_connected = target_device.get('connected', False)

            # 记录设备状态
            if is_connected:
                log.info(f"[BLUETOOTH] Target bluetooth device: {device_name} ({device_address})")
            else:
                log.warning(f"[BLUETOOTH] Bluetooth device not connected: {device_name} ({device_address})")

            # 格式: bluealsa:HCI=hci0,DEV=XX:XX:XX:XX:XX:XX,PROFILE=a2dp
            alsa_device = f"bluealsa:HCI={hci_adapter},DEV={device_address.upper()},PROFILE=a2dp"
            log.info(f"[BLUETOOTH] Using ALSA device: {alsa_device}")
            return alsa_device

        except Exception as e:
            log.error(f"[BLUETOOTH] Error getting ALSA device: {e}")
            return None


# 全局实例
bluetooth_mgr = BluetoothMgr()
