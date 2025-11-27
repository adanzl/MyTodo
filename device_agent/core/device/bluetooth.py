'''
蓝牙设备管理 (Linux Only)
'''
import asyncio
import shutil
import os
from typing import Dict, List, Optional
try:
    from core.log_config import root_logger
    log = root_logger()
except ImportError:
    import logging
    log = logging.getLogger()
    rds_mgr = None

# 尝试使用 gevent.subprocess，如果不可用则使用标准 subprocess
try:
    from gevent import subprocess, spawn
    GEVENT_AVAILABLE = True
except ImportError:
    import subprocess
    GEVENT_AVAILABLE = False
    spawn = None


from bleak import BleakScanner, BleakClient
from bleak.backends.scanner import AdvertisementData


class BluetoothDevice:
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


class BluetoothMgr:
    """蓝牙设备管理器"""

    def __init__(self):
        log.info("[BLUETOOTH] BluetoothMgr init")
        self.devices: Dict[str, BluetoothDevice] = {}  # address -> BluetoothDevice
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
                    addr_short = device.address.replace('-', '')[-6:].upper() if '-' in device.address else device.address[-6:].upper()
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
                                result = {
                                    'hex': data_bytes.hex(),
                                    'length': len(data_bytes)
                                }
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
                                    service_data_dict[str(service_uuid)] = {
                                        'hex': data.hex(),
                                        'length': len(data)
                                    }
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

                device_info = {
                    "address": device.address,
                    "name": friendly_name,
                    "metadata": metadata
                }
                device_list.append(device_info)

                # 更新设备列表
                if device.address not in self.devices:
                    self.devices[device.address] = BluetoothDevice(
                        address=device.address,
                        name=friendly_name,
                        metadata=metadata
                    )
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

    def _find_command(self, cmd_name):
        """
        查找命令的完整路径
        """
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
        """
        在 gevent 环境中安全地运行 subprocess
        """
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
                # 命令不存在
                log.warning(f"[BLUETOOTH] Command not found: {cmd[0] if isinstance(cmd, list) else cmd}")
                return -2, "", str(e)
            except Exception as e:
                log.error(f"[BLUETOOTH] Subprocess error: {e}")
                return -1, "", str(e)

        if GEVENT_AVAILABLE and spawn:
            # 在独立的 greenlet 中运行，避免线程问题
            greenlet = spawn(_run)
            return greenlet.get(timeout=timeout + 2)
        else:
            # 直接运行
            return _run()

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
                result_code, stdout, stderr = self._run_subprocess_safe(
                    ["bluetoothctl", "devices", "Paired"],
                    timeout=10
                )
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
                            result_code, stdout, stderr = self._run_subprocess_safe(
                                ["bluetoothctl", "info", address],
                                timeout=5
                            )
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
                    result_code, stdout, stderr = self._run_subprocess_safe(
                        ["hcitool", "con"],
                        timeout=10
                    )
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
    """
    同步扫描设备（在事件循环中运行）
    :param timeout: 扫描超时时间（秒）
    :return: 设备列表
    """
    import concurrent.futures
    try:
        # 尝试获取正在运行的事件循环
        asyncio.get_running_loop()
        # 如果有运行中的循环，需要在新线程中运行
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_async, get_bluetooth_mgr().scan_devices(timeout))
            # 设置超时时间，比扫描超时多5秒
            return future.result(timeout=timeout + 5.0)
    except RuntimeError:
        # 没有运行中的循环，创建新的事件循环
        return _run_async(get_bluetooth_mgr().scan_devices(timeout))
    except concurrent.futures.TimeoutError:
        log.error(f"[BLUETOOTH] Scan timeout after {timeout + 5.0}s")
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
    import concurrent.futures
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_async, get_bluetooth_mgr().connect_device(address), timeout=timeout)
            result = future.result(timeout=timeout + 5.0)
    except RuntimeError:
        result = _run_async(get_bluetooth_mgr().connect_device(address), timeout=timeout)
    except concurrent.futures.TimeoutError:
        log.error(f"[BLUETOOTH] Connect timeout after {timeout + 5.0}s")
        return {"code": -1, "msg": f"Connection timeout after {timeout}s"}
    except Exception as e:
        log.error(f"[BLUETOOTH] Connect error: {e}")
        return {"code": -1, "msg": f"Connection failed: {str(e)}"}

    return result


def disconnect_device_sync(address: str, timeout: float = 5.0) -> Dict:
    """同步断开设备"""
    import concurrent.futures
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_async, get_bluetooth_mgr().disconnect_device(address), timeout=timeout)
            result = future.result(timeout=timeout + 2.0)
    except RuntimeError:
        result = _run_async(get_bluetooth_mgr().disconnect_device(address), timeout=timeout)
    except concurrent.futures.TimeoutError:
        log.error(f"[BLUETOOTH] Disconnect timeout after {timeout + 2.0}s")
        return {"code": -1, "msg": f"Disconnect timeout after {timeout}s"}
    except Exception as e:
        log.error(f"[BLUETOOTH] Disconnect error: {e}")
        return {"code": -1, "msg": f"Disconnect failed: {str(e)}"}

    return result


def _run_async(coro, timeout: float = None):
    """在新的事件循环中运行协程"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if timeout:
            return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
        else:
            return loop.run_until_complete(coro)
    except asyncio.TimeoutError:
        log.error(f"[BLUETOOTH] Async operation timeout after {timeout}s")
        raise
    finally:
        try:
            # 取消所有待处理的任务
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            loop.close()
            asyncio.set_event_loop(None)


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
