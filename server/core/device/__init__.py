"""
设备模块
提供设备创建和管理功能
"""
from core.device.agent import DeviceAgent
from core.device.bluetooth import BluetoothDev
from core.device.dlna import DlnaDev
from core.device.mi_device import MiDevice


def create_device(node):
    """根据节点信息创建设备对象。

    Args:
        node: 设备节点信息，包含 type, address, name 等字段。

    Returns:
        包含 node 和 obj 的字典，obj 为设备对象实例；类型缺失或未知时 obj 为 None。
    """
    ret = {"node": node, "obj": None}
    # 用 .get 而非 []：调用方可能传入「没有配置设备」的空 dict（例如某条播放列表
    # 没选输出设备）。直接用 node["type"] 会抛 KeyError，而播放列表 reload 是整体
    # 事务性的——一条数据就能让整次加载失败，并在 5 秒后无限重试。
    # 缺失类型与「未知类型」语义一致：都不创建设备，返回 obj=None。
    device_type = node.get("type")
    if device_type == "agent":
        ret["obj"] = DeviceAgent(address=node["address"], name=node.get("name"))
    elif device_type == "bluetooth":
        ret["obj"] = BluetoothDev(node["address"], name=node.get("name"))
    elif device_type == "dlna":
        ret["obj"] = DlnaDev(node["address"], name=node.get("name"))
    elif device_type == "mi":
        ret["obj"] = MiDevice(address=node.get("address", ""), did=node.get("did"), name=node.get("name"))
    return ret
