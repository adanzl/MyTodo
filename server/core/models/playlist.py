"""
Playlist 业务相关工具函数
"""

import datetime
import json
import time
from typing import Dict, Any, List, Optional

from core.db import rds_mgr
from core.device.agent import DeviceAgent
from core.device.dlna import DlnaDev

PLAYLIST_RDS_FULL_KEY = f"schedule_play:playlist_collection"
DEFAULT_PLAYLIST_NAME = "默认播放列表"
DEVICE_TYPES = {"device_agent", "bluetooth", "dlna"}


def _generate_playlist_id() -> str:
    return f"pl_{int(time.time() * 1000)}"

_TS = lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ensure_str(value: Any, fallback: str = "") -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return fallback
    return str(value).strip()


def _create_device(node):
    ret = {"node": node, "obj": None}
    if node["type"] == "agent":
        ret["obj"] = DeviceAgent(node["address"])
    elif node["type"] == "bluetooth":
        ret["obj"] = None
    elif node["type"] == "dlna":
        ret["obj"] = DlnaDev(node["address"])
    return ret


class PlaylistMgr:

    def __init__(self):
        raw = rds_mgr.get(PLAYLIST_RDS_FULL_KEY)
        if raw:
            try:
                self.playlist_raw = json.loads(raw.decode("utf-8"))
                self._refresh_device_map()
            except (ValueError, AttributeError):
                self.playlist_raw = None
        else:
            self.playlist_raw = {}

    def get_playlist(self, id: str = None) -> Dict[str, Any] | None:
        if id is None:
            return self.playlist_raw
        return self.playlist_raw.get(id, None)

    def _create_playlist(self) -> Dict[str, Any]:
        now = _TS()
        return {
            "id": _generate_playlist_id(),
            "name": DEFAULT_PLAYLIST_NAME,
            "files": [],
            "current_index": 0,
            "schedule": {
                "enabled": 0,
                "cron": "",
                "duration": 0
            },
            "device": {
                "address": "",
                "type": "",
            },
            "create_time": now,
            "updated_time": now,
        }

    def save_playlist(self, collection: Dict[str, Any]) -> int:
        rds_mgr.set(PLAYLIST_RDS_FULL_KEY, json.dumps(collection, ensure_ascii=False))
        self.playlist_raw = collection
        # 更新设备映射
        self._refresh_device_map()
        return 0

    def _refresh_device_map(self):
        """刷新设备映射"""
        self.device_map = {}
        if self.playlist_raw:
            for p_id in self.playlist_raw:
                self.device_map[p_id] = _create_device(self.playlist_raw[p_id]["device"])
        # TODO 刷新定时任务

    def play(self, id: str) -> tuple[int, str]:
        """播放播放列表中当前索引的文件"""
        if not self.playlist_raw or id not in self.playlist_raw:
            return -1, "播放列表不存在"

        playlist_data = self.playlist_raw[id]
        files, current_index = playlist_data.get("files", []), playlist_data.get("current_index", 0)

        if not files:
            return -1, "播放列表为空"

        if current_index < 0 or current_index >= len(files):
            return -1, f"当前索引 {current_index} 超出范围"

        device_obj = self.device_map.get(id)
        if device_obj is None:
            return -1, "设备不存在或未初始化"

        file_path = files[current_index]
        return device_obj["obj"].play(file_path)

    def play_next(self, id: str) -> tuple[int, str]:
        """播放下一首"""
        if not self.playlist_raw or id not in self.playlist_raw:
            return -1, "播放列表不存在"

        playlist_data = self.playlist_raw[id]
        files, current_index = playlist_data.get("files", []), playlist_data.get("current_index", 0)

        next_index = (current_index + 1) % len(files)
        # 更新索引
        playlist_data["current_index"] = next_index
        playlist_data["updated_time"] = _TS()

        # 保存播放列表
        rds_mgr.set(PLAYLIST_RDS_FULL_KEY, json.dumps(self.playlist_raw, ensure_ascii=False))

        # 播放下一首
        code, msg = self.play(id)
        if code != 0:
            return -1, msg

        return 0, "播放下一首成功"

    def play_pre(self, id: str) -> tuple[int, str]:
        """播放上一首"""
        if not self.playlist_raw or id not in self.playlist_raw:
            return -1, "播放列表不存在"

        playlist_data = self.playlist_raw[id]
        files, current_index = playlist_data.get("files", []), playlist_data.get("current_index", 0)

        prev_index = (current_index - 1) % len(files)

        # 更新索引
        playlist_data["current_index"] = prev_index
        playlist_data["updated_time"] = _TS()

        # 保存播放列表
        rds_mgr.set(PLAYLIST_RDS_FULL_KEY, json.dumps(self.playlist_raw, ensure_ascii=False))

        # 播放上一首
        code, msg = self.play(id)
        if code != 0:
            return -1, msg

        return 0, "播放上一首成功"

    def stop(self, id: str) -> tuple[int, str]:
        """停止播放"""
        if not self.playlist_raw or id not in self.playlist_raw:
            return -1, "播放列表不存在"

        device_obj = self.device_map.get(id)
        if device_obj is None:
            return -1, "设备不存在或未初始化"

        return device_obj.stop()


playlist_mgr = PlaylistMgr()
