"""播放列表服务通用常量与小工具。

提取自 `core/services/playlist_mgr.py`，作为 P0 阶段的零风险拆分起点。
"""

import datetime
from typing import Callable

PLAYLIST_RDS_FULL_KEY = "schedule_play:playlist_collection"
PLAYLIST_RDS_HISTORY_KEY = "schedule_play:playlist_collection_history"
# 播放列表可用的输出设备类型。
#
# 必须是 "agent"（而不是 "device_agent"）：该值是**前端写入**的 device.type，
# 见 server/frontend/src/constants/device.ts（["agent", "dlna", "bluetooth", "mi"]），
# 后端 core/device/__init__.py 的 create_device 也按 "agent" 分派。
#
# 写成 "device_agent" 会让 agent 设备在 _build_device_spec 校验时被判为
# 「设备类型无效」而直接丢弃：该播放列表拿不到设备对象，播放永远不会开始
# （实测只有一行 warning，不报错：`设备类型无效: pl-agent, type=agent`）。
DEVICE_TYPES = {"agent", "bluetooth", "dlna", "mi"}


def _ts() -> str:
    """返回当前时间戳字符串。"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_TS: Callable[[], str] = _ts
