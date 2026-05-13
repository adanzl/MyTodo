"""播放列表服务通用常量与小工具。

提取自 `core/services/playlist_mgr.py`，作为 P0 阶段的零风险拆分起点。
"""

import datetime
from typing import Callable

PLAYLIST_RDS_FULL_KEY = "schedule_play:playlist_collection"
PLAYLIST_RDS_HISTORY_KEY = "schedule_play:playlist_collection_history"
DEVICE_TYPES = {"device_agent", "bluetooth", "dlna", "mi"}


def _ts() -> str:
    """返回当前时间戳字符串。"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_TS: Callable[[], str] = _ts
