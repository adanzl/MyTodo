'''
蓝牙设备管理路由
通过调用 device_agent 服务接口实现
'''
import os
import urllib.parse
from flask import Blueprint, json, request
from core.log_config import root_logger
from core.device_agent import get_device_agent_client

log = root_logger()
bluetooth_bp = Blueprint('bluetooth', __name__)


@bluetooth_bp.route("/bluetooth/scan", methods=['GET'])
def bluetooth_scan():
    """
    扫描蓝牙设备（通过 device_agent 服务）
    """
    try:
        timeout = request.args.get('timeout', 5.0, type=float)
        log.info(f"===== [Bluetooth Scan] timeout={timeout}")
        client = get_device_agent_client()
        result = client.bluetooth_scan(timeout)
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/devices", methods=['GET'])
def bluetooth_get_devices():
    """
    获取设备列表（通过 device_agent 服务）
    """
    try:
        log.info("===== [Bluetooth Get Devices]")
        client = get_device_agent_client()
        result = client.bluetooth_get_devices()
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/device", methods=['GET'])
def bluetooth_get_device():
    """
    获取设备信息（通过 device_agent 服务）
    """
    try:
        address = request.args.get('address')
        log.info(f"===== [Bluetooth Get Device] address={address}")
        if not address:
            return {"code": -1, "msg": "address is required"}
        client = get_device_agent_client()
        result = client.bluetooth_get_device(address)
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/connect", methods=['POST'])
def bluetooth_connect():
    """
    连接蓝牙设备（通过 device_agent 服务）
    """
    try:
        args = request.get_json()
        log.info("===== [Bluetooth Connect] " + json.dumps(args))
        address = args.get('address')
        if not address:
            return {"code": -1, "msg": "address is required"}
        client = get_device_agent_client()
        result = client.bluetooth_connect(address)
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/disconnect", methods=['POST'])
def bluetooth_disconnect():
    """
    断开蓝牙设备（通过 device_agent 服务）
    """
    try:
        args = request.get_json()
        log.info("===== [Bluetooth Disconnect] " + json.dumps(args))
        address = args.get('address')
        if not address:
            return {"code": -1, "msg": "address is required"}
        client = get_device_agent_client()
        result = client.bluetooth_disconnect(address)
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/connected", methods=['GET'])
def bluetooth_get_connected():
    """
    获取系统已连接的蓝牙设备列表（通过 device_agent 服务）
    """
    try:
        log.info("===== [Bluetooth Get Connected Devices]")
        client = get_device_agent_client()
        result = client.bluetooth_get_connected()
        return result
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@bluetooth_bp.route("/bluetooth/listDirectory", methods=['GET'])
def bluetooth_list_directory():
    """
    获取服务器目录列表
    """
    try:
        # 获取路径参数，并进行 URL 解码以支持中文和特殊字符
        path = request.args.get('path', '')
        if path:
            # URL 解码以支持中文字符和特殊字符
            # 可能需要多次解码（如果前端已经编码了）
            while '%' in path:
                try:
                    decoded = urllib.parse.unquote(path)
                    if decoded == path:
                        break
                    path = decoded
                except Exception:
                    break
        
        log.info(f"===== [Bluetooth List Directory] path={path}")
        
        # 默认基础目录
        default_base_dir = '/mnt'
        
        # 如果没有提供路径或路径为空，使用默认目录
        if not path or path == '':
            path = default_base_dir
        else:
            # 安全检查：防止路径遍历攻击
            # 检查路径中是否包含 .. 作为路径组件（不是文件名中的 ...）
            path_parts = path.split('/')
            if '..' in path_parts or path.startswith('~'):
                return {"code": -1, "msg": "Invalid path: Path traversal not allowed"}
            
            # 规范化路径
            if not os.path.isabs(path):
                # 如果是相对路径，从默认基础目录开始
                path = os.path.join(default_base_dir, path.lstrip('/'))
                path = os.path.abspath(path)
            else:
                path = os.path.abspath(path)
            
            # 确保路径在 /mnt 目录内（安全限制）
            if not path.startswith('/mnt'):
                log.warning(f"Path {path} is outside allowed directory /mnt, using default directory")
                path = default_base_dir
        
        # 验证路径
        if not os.path.exists(path):
            # 如果路径不存在，使用默认目录
            log.warning(f"Path does not exist: {path}, using default directory: {default_base_dir}")
            path = default_base_dir
        
        if not os.path.isdir(path):
            # 如果不是目录，使用默认目录
            log.warning(f"Path is not a directory: {path}, using default directory: {default_base_dir}")
            path = default_base_dir
        
        # 检查读取权限
        if not os.access(path, os.R_OK):
            # 如果没有读取权限，尝试使用默认目录
            if path != default_base_dir and os.access(default_base_dir, os.R_OK):
                log.warning(f"No read permission for {path}, using default directory: {default_base_dir}")
                path = default_base_dir
            else:
                return {"code": -1, "msg": f"Permission denied: No read permission for {path}"}
        
        # 获取目录内容
        items = []
        try:
            entries = os.listdir(path)
            for entry in entries:
                entry_path = os.path.join(path, entry)
                try:
                    # 检查是否有权限访问
                    if not os.access(entry_path, os.R_OK):
                        # 即使没有权限，也显示名称，但标记为不可访问
                        items.append({
                            "name": entry,
                            "isDirectory": os.path.isdir(entry_path) if os.path.exists(entry_path) else False,
                            "size": 0,
                            "modified": 0,
                            "accessible": False,
                        })
                        continue
                    
                    stat_info = os.stat(entry_path)
                    items.append({
                        "name": entry,
                        "isDirectory": os.path.isdir(entry_path),
                        "size": stat_info.st_size if os.path.isfile(entry_path) else 0,
                        "modified": stat_info.st_mtime,
                        "accessible": True,
                    })
                except (OSError, PermissionError) as e:
                    # 无法访问的文件/目录，但仍然显示名称
                    log.warning(f"Cannot access {entry_path}: {e}")
                    items.append({
                        "name": entry,
                        "isDirectory": False,
                        "size": 0,
                        "modified": 0,
                        "accessible": False,
                    })
                    continue
            
            # 排序：目录在前，然后按名称排序
            items.sort(key=lambda x: (not x["isDirectory"], x["name"].lower()))
            
            return {"code": 0, "msg": "ok", "data": items, "currentPath": path}
        except PermissionError as e:
            log.error(f"Permission denied for {path}: {e}")
            return {"code": -1, "msg": f"Permission denied: {str(e)}"}
        except Exception as e:
            log.error(f"Error listing directory: {e}")
            return {"code": -1, "msg": f"Error: {str(e)}"}
            
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}

