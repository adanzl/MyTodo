"""
设备模块
提供设备创建和管理功能
"""
from core.device.agent import DeviceAgent
from core.device.bluetooth import BluetoothDev
from core.device.dlna import DlnaDev
from core.device.mi_device import MiDevice


def create_device(node):
    """
    根据节点信息创建设备对象
    
    :param node: 设备节点信息，包含 type, address, name 等字段
    :return: 包含 node 和 obj 的字典，obj 为设备对象实例
    """
    ret = {"node": node, "obj": None}
    if node["type"] == "agent":
        ret["obj"] = DeviceAgent(address=node["address"], name=node.get("name"))
    elif node["type"] == "bluetooth":
        ret["obj"] = BluetoothDev(node["address"], name=node.get("name"))
    elif node["type"] == "dlna":
        ret["obj"] = DlnaDev(node["address"], name=node.get("name"))
    elif node["type"] == "mi":
        ret["obj"] = MiDevice(node.get("address", ""), name=node.get("name"))
    return ret
