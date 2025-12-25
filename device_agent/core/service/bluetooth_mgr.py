'''
蓝牙设备管理 (Linux Only) - 使用 DBus + BlueZ
'''
import asyncio
from typing import Dict, List, Optional, Any

import dbus
import dbus.exceptions

from bleak import BleakScanner
from bleak.backends.scanner import AdvertisementData

from core.device.bluetooth_dev import BluetoothDev
from core.log_config import root_logger
from core.utils import run_async

log = root_logger()

# 常量定义
DEFAULT_ADAPTER = 'hci0'
BLUEZ_SERVICE = 'org.bluez'
BLUEZ_ROOT_PATH = '/'
ADAPTER_INTERFACE = 'org.bluez.Adapter1'
DEVICE_INTERFACE = 'org.bluez.Device1'
PROPERTIES_INTERFACE = 'org.freedesktop.DBus.Properties'
OBJECT_MANAGER_INTERFACE = 'org.freedesktop.DBus.ObjectManager'
CONNECTION_WAIT_TIME = 0.5  # 连接后等待时间（秒）
PRINTABLE_RATIO_THRESHOLD = 0.7  # 可打印字符比例阈值


class BluetoothMgr:
    """蓝牙设备管理器（使用 DBus + BlueZ）"""

    def __init__(self):
        log.info("[BLUETOOTH] BluetoothMgr init (DBus + BlueZ)")
        self.devices: Dict[str, BluetoothDev] = {}  # address -> BluetoothDev
        self.scanning = False
        self._scan_task = None
        # 存储每个适配器的 DBus 连接信息
        self._adapter_buses: Dict[str, dbus.SystemBus] = {}
        self._adapter_paths: Dict[str, str] = {}
        self._adapter_interfaces: Dict[str, dbus.Interface] = {}
        self._default_adapter = DEFAULT_ADAPTER
        # DBus manager 缓存（按 bus 缓存）
        self._dbus_managers: Dict[dbus.SystemBus, dbus.Interface] = {}
        # 初始化 DBus
        self._init_dbus()

    def _init_dbus(self):
        """初始化 DBus 连接"""
        try:
            # 设置 DBus main loop（如果需要）
            from dbus.mainloop.glib import DBusGMainLoop
            DBusGMainLoop(set_as_default=True)
        except Exception as e:
            log.debug(f"[BLUETOOTH] DBus main loop setup skipped: {e}")

    def _get_dbus_manager(self, bus: dbus.SystemBus) -> dbus.Interface:
        """
        获取或创建 DBus ObjectManager 接口（带缓存）
        :param bus: DBus 系统总线
        :return: ObjectManager 接口
        """
        if bus not in self._dbus_managers:
            self._dbus_managers[bus] = dbus.Interface(bus.get_object(BLUEZ_SERVICE, BLUEZ_ROOT_PATH),
                                                      OBJECT_MANAGER_INTERFACE)
        return self._dbus_managers[bus]

    def _find_adapter_path(self, adapter_name: str, objects: Dict) -> Optional[str]:
        """
        查找适配器路径
        :param adapter_name: 适配器名称（如 hci0）
        :param objects: GetManagedObjects() 返回的对象字典
        :return: 适配器路径，如果未找到返回 None
        """
        # 首先尝试通过路径查找适配器（路径格式：/org/bluez/hci0）
        for path, interfaces in objects.items():
            if ADAPTER_INTERFACE in interfaces:
                # 从路径中提取 hci 名称
                if path.startswith('/org/bluez/'):
                    path_hci = path.split('/')[-1]
                    if path_hci == adapter_name:
                        return path
                # 备用方案：检查路径中是否包含适配器名称
                elif adapter_name in path:
                    return path

        # 如果没找到指定适配器，返回第一个适配器
        for path, interfaces in objects.items():
            if ADAPTER_INTERFACE in interfaces:
                return path

        return None

    def get_adapters(self) -> List[Dict[str, Any]]:
        """获取所有可用的蓝牙适配器列表"""
        try:
            bus = dbus.SystemBus()
            manager = self._get_dbus_manager(bus)
            objects = manager.GetManagedObjects()
            default_adapter = self._default_adapter
            adapters = []
            
            for path, interfaces in objects.items():
                if ADAPTER_INTERFACE not in interfaces:
                    continue
                    
                adapter_props = interfaces[ADAPTER_INTERFACE]
                system_name = adapter_props.get('Name', '')
                
                # 从路径中提取 hci 名称（如 /org/bluez/hci0 -> hci0）
                hci_name = path.split('/')[-1] if path.startswith('/org/bluez/') else \
                           next((p for p in reversed(path.split('/')) if p.startswith('hci')), system_name or 'unknown')
                
                adapter_info = {
                    'name': hci_name,
                    'system_name': system_name,
                    'path': path,
                    'powered': bool(adapter_props.get('Powered', False)),
                    'discoverable': bool(adapter_props.get('Discoverable', False)),
                    'pairable': bool(adapter_props.get('Pairable', False)),
                    'discovering': bool(adapter_props.get('Discovering', False)),
                    'address': adapter_props.get('Address', ''),
                    'is_default': hci_name == default_adapter,
                }
                if 'Class' in adapter_props:
                    adapter_info['class'] = int(adapter_props['Class'])
                adapters.append(adapter_info)

            log.info(f"[BLUETOOTH] Found {len(adapters)} adapters, default: {default_adapter}")
            return adapters
        except Exception as e:
            log.error(f"[BLUETOOTH] Failed to get adapters: {e}")
            return []

    def get_default_adapter(self) -> str:
        """获取默认适配器名称"""
        return self._default_adapter

    def set_default_adapter(self, adapter: str) -> Dict[str, Any]:
        """设置默认适配器"""
        try:
            adapters = self.get_adapters()
            adapter_names = [a.get('name') for a in adapters]
            if adapter not in adapter_names:
                return {"code": -1, "msg": f"Adapter {adapter} not found. Available: {', '.join(adapter_names)}"}
            
            old_adapter = self._default_adapter
            self._default_adapter = adapter
            
            # 清除旧适配器的缓存
            for cache_dict in [self._adapter_interfaces, self._adapter_buses, self._adapter_paths]:
                cache_dict.pop(old_adapter, None)
            
            log.info(f"[BLUETOOTH] Default adapter changed from {old_adapter} to {adapter}")
            return {"code": 0, "msg": f"Default adapter set to {adapter}", "data": {"adapter": adapter}}
        except Exception as e:
            log.error(f"[BLUETOOTH] Failed to set default adapter: {e}")
            return {"code": -1, "msg": f"Failed to set default adapter: {str(e)}"}

    def _get_adapter_info(self, adapter: str = None) -> Optional[Dict[str, Any]]:
        """获取适配器的 DBus 信息"""
        adapter = adapter or self._default_adapter

        # 如果已经初始化过，直接返回
        if adapter in self._adapter_interfaces and self._adapter_interfaces[adapter]:
            return {
                'bus': self._adapter_buses[adapter],
                'path': self._adapter_paths[adapter],
                'interface': self._adapter_interfaces[adapter]
            }

        try:
            # 创建 DBus 连接
            bus = dbus.SystemBus()

            # 查找适配器路径
            manager = self._get_dbus_manager(bus)
            objects = manager.GetManagedObjects()
            adapter_path = self._find_adapter_path(adapter, objects)

            if not adapter_path:
                log.warning(f"[BLUETOOTH] Adapter {adapter} not found")
                return None

            # 创建适配器接口
            obj = bus.get_object(BLUEZ_SERVICE, adapter_path)
            adapter_interface = dbus.Interface(obj, ADAPTER_INTERFACE)

            # 缓存信息
            self._adapter_buses[adapter] = bus
            self._adapter_paths[adapter] = adapter_path
            self._adapter_interfaces[adapter] = adapter_interface

            log.info(f"[BLUETOOTH] Initialized adapter: {adapter} at {adapter_path}")
            return {'bus': bus, 'path': adapter_path, 'interface': adapter_interface}

        except dbus.exceptions.DBusException as e:
            log.error(f"[BLUETOOTH] DBus error for adapter {adapter}: {e}")
            log.error(f"[BLUETOOTH] Make sure BlueZ service is running: sudo systemctl status bluetooth")
            return None
        except Exception as e:
            log.error(f"[BLUETOOTH] Failed to get adapter info for {adapter}: {e}")
            return None

    def _get_device_path(self, address: str, adapter: str = None) -> Optional[str]:
        """获取设备路径"""
        try:
            adapter_info = self._get_adapter_info(adapter)
            if not adapter_info:
                return None

            bus = adapter_info['bus']
            manager = self._get_dbus_manager(bus)
            objects = manager.GetManagedObjects()

            address_upper = address.upper()
            for path, interfaces in objects.items():
                if DEVICE_INTERFACE in interfaces:
                    device_props = interfaces[DEVICE_INTERFACE]
                    device_address = device_props.get('Address', '').upper()
                    if device_address == address_upper:
                        return path

            return None
        except Exception as e:
            log.error(f"[BLUETOOTH] Failed to get device path for {address}: {e}")
            return None

    def _get_devices_from_dbus(self, adapter: str = None) -> List[Dict[str, Any]]:
        """从 DBus 获取所有设备"""
        try:
            adapter_info = self._get_adapter_info(adapter)
            if not adapter_info:
                return []

            bus = adapter_info['bus']
            manager = self._get_dbus_manager(bus)
            objects = manager.GetManagedObjects()

            devices = []
            for path, interfaces in objects.items():
                if DEVICE_INTERFACE in interfaces:
                    device_props = interfaces[DEVICE_INTERFACE]
                    address = device_props.get('Address', '')
                    name = device_props.get('Name', '')
                    paired = device_props.get('Paired', False)
                    connected = device_props.get('Connected', False)
                    trusted = device_props.get('Trusted', False)
                    rssi = device_props.get('RSSI', None)
                    uuids = device_props.get('UUIDs', [])

                    devices.append({
                        'address': address.upper() if address else '',
                        'name': name or address or 'Unknown',
                        'paired': bool(paired),
                        'connected': bool(connected),
                        'trusted': bool(trusted),
                        'rssi': int(rssi) if rssi is not None else None,
                        'uuids': [str(uuid) for uuid in uuids] if uuids else [],
                        'path': path
                    })

            return devices
        except Exception as e:
            log.error(f"[BLUETOOTH] Failed to get devices from DBus: {e}")
            return []

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

    def _get_friendly_name(self, device, advertisement_data: Optional[AdvertisementData]) -> str:
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

    async def scan_devices(self, timeout: float = 5.0, adapter: str = None) -> List[Dict]:
        """扫描传统蓝牙设备（使用 DBus + BlueZ）"""
        if self.scanning:
            log.warning("[BLUETOOTH] Already scanning")
            return []

        try:
            self.scanning = True
            adapter = adapter or self._default_adapter
            log.info(f"[BLUETOOTH] Starting classic bluetooth scan on {adapter} (timeout: {timeout}s)")

            # 获取适配器信息
            adapter_info = self._get_adapter_info(adapter)
            if not adapter_info:
                log.error(f"[BLUETOOTH] Failed to get adapter info for {adapter}")
                return []

            adapter_interface = adapter_info['interface']

            # 开始扫描
            try:
                adapter_interface.StartDiscovery()
                log.info(f"[BLUETOOTH] Started discovery on {adapter}")
            except dbus.exceptions.DBusException as e:
                log.error(f"[BLUETOOTH] Failed to start discovery: {e}")
                return []

            # 等待扫描时间
            await asyncio.sleep(timeout)

            # 停止扫描
            try:
                adapter_interface.StopDiscovery()
                log.info(f"[BLUETOOTH] Stopped discovery on {adapter} after {timeout}s")
            except dbus.exceptions.DBusException as e:
                log.warning(f"[BLUETOOTH] Failed to stop discovery: {e}")

            # 获取扫描到的设备
            devices = self._get_devices_from_dbus(adapter)

            # 只返回未配对的设备（即扫描到的新设备）
            device_list = []
            for device in devices:
                # 跳过已配对的设备，只返回扫描到的新设备
                if device.get('paired', False):
                    continue

                address = device['address']
                device_info = {
                    "address": address,
                    "name": device['name'],
                    "metadata": {
                        "connected": device['connected'],
                        "paired": device['paired'],
                        "trusted": device['trusted'],
                        "rssi": device['rssi'],
                        "uuids": device['uuids']
                    }
                }

                device_list.append(device_info)

                # 更新设备列表
                self._update_or_create_device(address=address,
                                              name=device_info["name"],
                                              metadata=device_info.get("metadata", {}))

            log.info(
                f"[BLUETOOTH] Found {len(device_list)} scanned classic bluetooth devices (excluding paired devices)")
            return device_list

        except Exception as e:
            log.error(f"[BLUETOOTH] Classic bluetooth scan error: {e}")
            return []
        finally:
            self.scanning = False

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

    async def connect_device(self, address: str, adapter: str = None) -> Dict:
        """连接蓝牙设备（使用 DBus + BlueZ）"""
        address_upper = address.upper()
        adapter = adapter or self._default_adapter

        try:
            # 获取适配器信息
            adapter_info = self._get_adapter_info(adapter)
            if not adapter_info:
                return {"code": -1, "msg": f"Failed to get adapter info for {adapter}"}

            bus = adapter_info['bus']

            # 检查设备是否已连接
            device_info_result = self._get_device_info_from_dbus(address_upper, bus, adapter)
            if device_info_result.get('code') == 0:
                device_info = device_info_result.get('data', {})
                if device_info.get('connected'):
                    log.info(f"[BLUETOOTH] Device {address_upper} is already connected")
                    # 确保设备在管理器中
                    device = self._update_or_create_device(address=address_upper,
                                                           name=device_info.get('name', address_upper),
                                                           metadata=device_info)
                    device.connected = True
                    return {"code": 0, "msg": "Already connected", "data": device.to_dict()}

            # 执行连接
            log.info(f"[BLUETOOTH] Connecting to device: {address_upper} on {adapter}")
            result = self._connect_device_via_dbus(address_upper, bus, adapter)

            if result.get('code') == 0:
                # 等待连接完成
                await asyncio.sleep(CONNECTION_WAIT_TIME)

                # 获取设备信息并更新管理器
                device_info_result = self._get_device_info_from_dbus(address_upper, bus, adapter)
                if device_info_result.get('code') == 0:
                    device_info = device_info_result.get('data', {})
                    device = self._update_or_create_device(address=address_upper,
                                                           name=device_info.get('name', address_upper),
                                                           metadata=device_info)
                    device.connected = True
                    return {"code": 0, "msg": "Connected", "data": device.to_dict()}
                else:
                    return {"code": 0, "msg": "Connected"}
            else:
                return result

        except Exception as e:
            log.error(f"[BLUETOOTH] Connect error for {address_upper}: {e}")
            if address_upper in self.devices:
                self.devices[address_upper].connected = False
            return {"code": -1, "msg": f"Connection failed: {str(e)}"}

    async def disconnect_device(self, address: str, adapter: str = None) -> Dict:
        """断开蓝牙设备（使用 DBus + BlueZ）"""
        address_upper = address.upper()
        adapter = adapter or self._default_adapter

        try:
            # 获取适配器信息
            adapter_info = self._get_adapter_info(adapter)
            if not adapter_info:
                return {"code": -1, "msg": f"Failed to get adapter info for {adapter}"}

            bus = adapter_info['bus']

            # 检查设备是否已断开
            device_info_result = self._get_device_info_from_dbus(address_upper, bus, adapter)
            if device_info_result.get('code') == 0 and not device_info_result.get('data', {}).get('connected'):
                log.info(f"[BLUETOOTH] Device {address_upper} is already disconnected")
                if address_upper in self.devices:
                    self.devices[address_upper].connected = False
                return {"code": 0, "msg": "Already disconnected"}

            # 执行断开
            log.info(f"[BLUETOOTH] Disconnecting device: {address_upper} on {adapter}")
            result = self._disconnect_device_via_dbus(address_upper, bus, adapter)

            # 更新管理器状态
            if address_upper in self.devices:
                self.devices[address_upper].connected = False
                self.devices[address_upper].client = None

            if result.get('code') == 0:
                if address_upper in self.devices:
                    return {"code": 0, "msg": "Disconnected", "data": self.devices[address_upper].to_dict()}
                return {"code": 0, "msg": "Disconnected"}
            return result

        except Exception as e:
            log.error(f"[BLUETOOTH] Disconnect error for {address_upper}: {e}")
            if address_upper in self.devices:
                self.devices[address_upper].connected = False
            return {"code": -1, "msg": f"Disconnect failed: {str(e)}"}

    def trust_device(self, address: str, adapter: str = None) -> Dict:
        """信任蓝牙设备（使用 DBus + BlueZ）"""
        address_upper = address.upper()
        adapter = adapter or self._default_adapter

        try:
            adapter_info = self._get_adapter_info(adapter)
            if not adapter_info:
                return {"code": -1, "msg": f"Failed to get adapter info for {adapter}"}

            bus = adapter_info['bus']
            device_path = self._get_device_path(address_upper, adapter)

            if not device_path:
                return {"code": -1, "msg": f"Device {address_upper} not found"}

            device_obj = bus.get_object(BLUEZ_SERVICE, device_path)
            device_props = dbus.Interface(device_obj, PROPERTIES_INTERFACE)
            device_props.Set(DEVICE_INTERFACE, 'Trusted', True)

            log.info(f"[BLUETOOTH] Trusted device: {address_upper} on {adapter}")
            return {"code": 0, "msg": "Device trusted"}
        except dbus.exceptions.DBusException as e:
            log.error(f"[BLUETOOTH] Failed to trust device {address_upper}: {e}")
            return {"code": -1, "msg": f"Trust failed: {str(e)}"}
        except Exception as e:
            log.error(f"[BLUETOOTH] Trust error for {address_upper}: {e}")
            return {"code": -1, "msg": f"Trust failed: {str(e)}"}

    def scan_devices_sync(self, timeout: float = 5.0, adapter: str = None) -> List[Dict]:
        """
        同步扫描传统蓝牙设备（在事件循环中运行）
        :param timeout: 扫描超时时间（秒）
        :param adapter: HCI 适配器名称，默认为默认适配器
        :return: 设备列表
        """
        try:
            return run_async(self.scan_devices(timeout, adapter), timeout=timeout + 2, log_prefix="BLUETOOTH")
        except asyncio.TimeoutError:
            log.error(f"[BLUETOOTH] Classic bluetooth scan timeout after {timeout}s")
            return []
        except Exception as e:
            log.error(f"[BLUETOOTH] Classic bluetooth scan error: {e}")
            return []

    def scan_ble_devices_sync(self, timeout: float = 5.0) -> List[Dict]:
        """
        同步扫描 BLE 蓝牙设备（在事件循环中运行）
        :param timeout: 扫描超时时间（秒）
        :return: 设备列表
        """
        try:
            return run_async(self.scan_ble_devices(timeout), timeout=timeout, log_prefix="BLUETOOTH")
        except asyncio.TimeoutError:
            log.error(f"[BLUETOOTH] BLE scan timeout after {timeout}s")
            return []
        except Exception as e:
            log.error(f"[BLUETOOTH] BLE scan error: {e}")
            return []

    def _connect_device_via_dbus(self, address: str, bus: dbus.SystemBus, adapter: str = None) -> Dict[str, Any]:
        """通过 DBus 连接设备"""
        try:
            device_path = self._get_device_path(address, adapter)
            if not device_path:
                return {"code": -1, "msg": f"Device {address} not found"}

            device_obj = bus.get_object(BLUEZ_SERVICE, device_path)
            device_interface = dbus.Interface(device_obj, DEVICE_INTERFACE)
            device_interface.Connect()

            return {"code": 0, "msg": "Connected"}
        except dbus.exceptions.DBusException as e:
            error_name = e.get_dbus_name()
            if 'org.bluez.Error.AlreadyConnected' in error_name:
                return {"code": 0, "msg": "Already connected"}
            log.error(f"[BLUETOOTH] Failed to connect device {address}: {e}")
            return {"code": -1, "msg": f"Connection failed: {str(e)}"}
        except Exception as e:
            log.error(f"[BLUETOOTH] Connect error: {e}")
            return {"code": -1, "msg": f"Connection failed: {str(e)}"}

    def _disconnect_device_via_dbus(self, address: str, bus: dbus.SystemBus, adapter: str = None) -> Dict[str, Any]:
        """通过 DBus 断开设备"""
        try:
            device_path = self._get_device_path(address, adapter)
            if not device_path:
                return {"code": -1, "msg": f"Device {address} not found"}

            device_obj = bus.get_object(BLUEZ_SERVICE, device_path)
            device_interface = dbus.Interface(device_obj, DEVICE_INTERFACE)
            device_interface.Disconnect()
            log.info(f"[BLUETOOTH] Disconnected device: {address}")
            return {"code": 0, "msg": "Disconnected"}
        except dbus.exceptions.DBusException as e:
            if 'org.bluez.Error.NotConnected' in e.get_dbus_name():
                return {"code": 0, "msg": "Already disconnected"}
            log.error(f"[BLUETOOTH] Failed to disconnect device {address}: {e}")
            return {"code": -1, "msg": f"Disconnect failed: {str(e)}"}
        except Exception as e:
            log.error(f"[BLUETOOTH] Disconnect error: {e}")
            return {"code": -1, "msg": f"Disconnect failed: {str(e)}"}

    def _get_device_info_from_dbus(self, address: str, bus: dbus.SystemBus, adapter: str = None) -> Dict[str, Any]:
        """从 DBus 获取设备详细信息"""
        try:
            device_path = self._get_device_path(address, adapter)
            if not device_path:
                return {"code": -1, "msg": f"Device {address} not found"}

            device_obj = bus.get_object(BLUEZ_SERVICE, device_path)
            device_props = dbus.Interface(device_obj, PROPERTIES_INTERFACE)
            device1_props = device_props.GetAll(DEVICE_INTERFACE)

            info = {
                'address': address.upper(),
                'name': device1_props.get('Name', ''),
                'paired': bool(device1_props.get('Paired', False)),
                'connected': bool(device1_props.get('Connected', False)),
                'trusted': bool(device1_props.get('Trusted', False)),
                'rssi': int(device1_props.get('RSSI', 0)) if device1_props.get('RSSI') is not None else None,
                'uuids': [str(uuid) for uuid in device1_props.get('UUIDs', [])],
            }

            # 添加 Class（如果可用）
            if 'Class' in device1_props:
                info['class'] = int(device1_props['Class'])

            return {"code": 0, "msg": "Device found", "data": info}
        except dbus.exceptions.DBusException as e:
            log.error(f"[BLUETOOTH] Failed to get device info {address}: {e}")
            return {"code": -1, "msg": f"Failed to get device info: {str(e)}"}
        except Exception as e:
            log.error(f"[BLUETOOTH] Get device info error: {e}")
            return {"code": -1, "msg": f"Failed to get device info: {str(e)}"}

    def _check_device_connected(self, address: str, adapter: str = None) -> bool:
        """检查设备是否已连接"""
        try:
            adapter_info = self._get_adapter_info(adapter)
            if not adapter_info:
                return False
            result = self._get_device_info_from_dbus(address, adapter_info['bus'], adapter)
            return result.get('code') == 0 and result.get('data', {}).get('connected', False)
        except Exception as e:
            log.debug(f"[BLUETOOTH] Failed to check connection status for {address}: {e}")
            return False

    def get_paired_devices(self, adapter: str = None) -> List[Dict]:
        """获取系统已配对的蓝牙设备列表"""
        try:
            devices = self._get_devices_from_dbus(adapter)
            paired_devices = [d for d in devices if d.get('paired', False)]
            adapter_name = adapter or self._default_adapter
            log.info(f"[BLUETOOTH] Found {len(paired_devices)} paired devices on {adapter_name}")
            return paired_devices
        except Exception as e:
            log.error(f"[BLUETOOTH] Error getting paired devices: {e}")
            return []

    def get_connected_devices(self, adapter: str = None) -> List[Dict]:
        """获取所有已连接的设备"""
        try:
            devices = self._get_devices_from_dbus(adapter)
            connected_devices = [d for d in devices if d.get('connected', False)]
            result = []
            for device in connected_devices:
                address = device['address']
                if address in self.devices:
                    device_dict = self.devices[address].to_dict()
                    device_dict["connected"] = True
                    result.append(device_dict)
                else:
                    result.append(device)
            adapter_name = adapter or self._default_adapter
            log.info(f"[BLUETOOTH] Found {len(result)} connected devices on {adapter_name}")
            return result
        except Exception as e:
            log.error(f"[BLUETOOTH] Error getting connected devices: {e}")
            return []

    def connect_device_sync(self, address: str, timeout: float = 10.0, adapter: str = None) -> Dict:
        """同步连接设备"""
        try:
            return run_async(self.connect_device(address, adapter), timeout=timeout, log_prefix="BLUETOOTH")
        except (asyncio.TimeoutError, Exception) as e:
            msg = f"Connection timeout after {timeout}s" if isinstance(e, asyncio.TimeoutError) else f"Connection failed: {str(e)}"
            log.error(f"[BLUETOOTH] Connect error: {e}")
            return {"code": -1, "msg": msg}

    def disconnect_device_sync(self, address: str, timeout: float = 5.0, adapter: str = None) -> Dict:
        """同步断开设备"""
        try:
            return run_async(self.disconnect_device(address, adapter), timeout=timeout, log_prefix="BLUETOOTH")
        except (asyncio.TimeoutError, Exception) as e:
            msg = f"Disconnect timeout after {timeout}s" if isinstance(e, asyncio.TimeoutError) else f"Disconnect failed: {str(e)}"
            log.error(f"[BLUETOOTH] Disconnect error: {e}")
            return {"code": -1, "msg": msg}

    def _find_target_device(self, device_address: Optional[str], paired_devices: List[Dict]) -> Optional[Dict]:
        """查找目标蓝牙设备"""
        if device_address:
            addr_upper = device_address.upper()
            target = next((d for d in paired_devices if d.get('address', '').upper() == addr_upper), None)
            if not target:
                log.warning(f"[BLUETOOTH] Bluetooth device not found: {device_address}")
                return {'address': device_address, 'name': device_address, 'connected': False}
            return target
        else:
            target = next((d for d in paired_devices if d.get('connected')), None)
            if not target:
                log.warning("[BLUETOOTH] No connected bluetooth devices found")
                target = paired_devices[0] if paired_devices else None
                if target:
                    log.info(f"[BLUETOOTH] Using first paired device: {target.get('name')}")
            return target

    def get_alsa_name(self, device_address: Optional[str] = None, hci_adapter: str = 'hci0') -> Optional[str]:
        """获取 ALSA 蓝牙音频设备名称"""
        try:
            paired_devices = self.get_paired_devices(hci_adapter)
            if not paired_devices:
                log.warning(f"[BLUETOOTH] No paired bluetooth devices found on {hci_adapter}")
                return None

            target_device = self._find_target_device(device_address, paired_devices)
            if not target_device:
                return None

            addr = target_device.get('address')
            name = target_device.get('name', addr)
            is_connected = target_device.get('connected', False)

            if is_connected:
                log.info(f"[BLUETOOTH] Target bluetooth device: {name} ({addr})")
            else:
                log.warning(f"[BLUETOOTH] Bluetooth device not connected: {name} ({addr})")

            alsa_device = f"bluealsa:HCI={hci_adapter},DEV={addr.upper()},PROFILE=a2dp"
            log.info(f"[BLUETOOTH] Using ALSA device: {alsa_device}")
            return alsa_device
        except Exception as e:
            log.error(f"[BLUETOOTH] Error getting ALSA device: {e}")
            return None

    def get_info(self, address: str, adapter: str = None) -> Dict:
        """获取指定设备的信息"""
        try:
            address_upper = address.upper()
            adapter_info = self._get_adapter_info(adapter)
            if not adapter_info:
                return {"code": -1, "msg": f"Failed to get adapter info for {adapter}"}

            result = self._get_device_info_from_dbus(address_upper, adapter_info['bus'], adapter)

            # 如果设备在管理器中，合并信息
            if result.get('code') == 0 and address_upper in self.devices:
                merged_info = self.devices[address_upper].to_dict()
                merged_info.update(result.get('data', {}))
                result['data'] = merged_info

            return result
        except Exception as e:
            log.error(f"[BLUETOOTH] Error getting device info: {e}")
            return {"code": -1, "msg": f"Failed to get device info: {str(e)}"}


# 全局实例
bluetooth_mgr = BluetoothMgr()
