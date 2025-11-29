import datetime
import json
import os
import sys
import time
from datetime import timedelta
from typing import Dict, Any, List, Optional

from core.db import rds_mgr
from core.device.agent import DeviceAgent
from core.device.dlna import DlnaDev
from core.log_config import root_logger
from core.scheduler import get_scheduler
from core.api.routes import get_media_duration

log = root_logger()

PLAYLIST_RDS_FULL_KEY = f"schedule_play:playlist_collection"
DEFAULT_PLAYLIST_NAME = "默认播放列表"
DEVICE_TYPES = {"device_agent", "bluetooth", "dlna"}

def _generate_playlist_id() -> str:
    return f"pl_{int(time.time() * 1000)}"

_TS = lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _create_device(node):
    ret = {"node": node, "obj": None}
    if node["type"] in ("agent", "bluetooth"):
        ret["obj"] = DeviceAgent(node["address"])
    elif node["type"] == "dlna":
        ret["obj"] = DlnaDev(node["address"])
    return ret

def _get_file_uri(file_item):
    if isinstance(file_item, str):
        return file_item
    if isinstance(file_item, dict):
        return file_item.get("uri") or file_item.get("path") or file_item.get("file") or ""
    return ""


class PlaylistMgr:

    def __init__(self):
        self._polling_playlists = set()
        self._polling_interval = 1
        self._scheduled_play_start_times = {}
        self.reload()

    def get_playlist(self, id: str) -> Dict[str, Any] | None:
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
                "name": "",
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

    def reload(self) -> int:
        """
        重新从 RDS 中加载 playlist 数据
        """
        try:
            raw = rds_mgr.get(PLAYLIST_RDS_FULL_KEY)
            if raw:
                try:
                    self.playlist_raw = json.loads(raw.decode("utf-8"))
                    self._refresh_device_map()
                except (ValueError, AttributeError) as e:
                    log.error(f"[PlaylistMgr] Reload error: {e}")
                    self.playlist_raw = {}
                    self._refresh_device_map()
            else:
                self.playlist_raw = {}
                self._refresh_device_map()
            log.info(f"[PlaylistMgr] Load success: {len(self.playlist_raw)} playlists")
            return 0
        except Exception as e:
            log.error(f"[PlaylistMgr] Reload error: {e}")
            return -1

    def _refresh_device_map(self):
        self.device_map = {}
        if self.playlist_raw and sys.platform != "win32":
            for p_id in self.playlist_raw:
                playlist_data = self.playlist_raw[p_id]
                self.device_map[p_id] = _create_device(playlist_data.get("device", {}))
                self._refresh_cron_job(p_id, playlist_data)
        self._cleanup_orphaned_cron_jobs()

    def _refresh_cron_job(self, playlist_id: str, playlist_data: Dict[str, Any]):
        scheduler = get_scheduler()
        job_id = f"playlist_cron_{playlist_id}"
        schedule = playlist_data.get("schedule", {})
        enabled = schedule.get("enabled", 0)
        cron_expression = schedule.get("cron", "").strip()

        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        if enabled != 1 or not cron_expression:
            return

        def cron_play_task(pid=playlist_id):
            # log.info(f"[PlaylistMgr] 定时任务播放成功: {pid}")
            try:
                code, msg = self.play(pid)
                if code == 0:
                    self._scheduled_play_start_times[pid] = datetime.datetime.now()
                    log.info(f"[PlaylistMgr] 定时任务播放成功: {pid}")
                else:
                    log.error(f"[PlaylistMgr] 定时任务播放失败: {pid}, {msg}")
            except Exception as e:
                log.error(f"[PlaylistMgr] 定时任务执行异常: {pid}, {e}")

        success = scheduler.add_cron_job(func=cron_play_task, job_id=job_id, cron_expression=cron_expression)
        playlist_name = playlist_data.get("name", "未知播放列表")
        if success:
            log.info(f"[PlaylistMgr] 创建定时任务成功: {playlist_id}, {playlist_name}, cron: {cron_expression}")
        else:
            log.error(f"[PlaylistMgr] 创建定时任务失败: {playlist_id}, {playlist_name}, cron: {cron_expression}")

    def _cleanup_orphaned_cron_jobs(self):
        scheduler = get_scheduler()
        playlist_ids = set(self.playlist_raw.keys() if self.playlist_raw else [])

        for job in scheduler.get_all_jobs():
            if job.id.startswith("playlist_cron_"):
                playlist_id = job.id.replace("playlist_cron_", "", 1)
                if playlist_id not in playlist_ids:
                    scheduler.remove_job(job.id)
                    log.info(f"[PlaylistMgr] 清理孤立的定时任务: {job.id}")

        for playlist_id in list(self._scheduled_play_start_times.keys()):
            if playlist_id not in playlist_ids:
                del self._scheduled_play_start_times[playlist_id]

    def _validate_playlist(self, id: str):
        if not self.playlist_raw or id not in self.playlist_raw:
            return None, -1, "播放列表不存在"
        playlist_data = self.playlist_raw[id]
        files = playlist_data.get("files", [])
        if not files:
            return None, -1, "播放列表为空"
        device_obj = self.device_map.get(id)
        if device_obj is None:
            return None, -1, "设备不存在或未初始化"
        return playlist_data, 0, None

    def play(self, id: str) -> tuple[int, str]:
        playlist_data, code, msg = self._validate_playlist(id)
        if code != 0:
            return code, msg

        files = playlist_data.get("files", [])
        current_index = playlist_data.get("current_index", 0)
        if current_index < 0 or current_index >= len(files):
            return -1, f"当前索引 {current_index} 超出范围"

        file_path = _get_file_uri(files[current_index])
        
        if not file_path:
            return -1, "文件路径无效"

        # 获取并更新文件时长
       
        duration = get_media_duration(file_path)
        if duration is not None:
            # 更新当前播放文件的时长
            files[current_index]["duration"] = duration

        device = self.device_map[id]["obj"]
        code, msg = device.play(file_path)
        if code != 0:
            return code, msg

        if device.get_transport_info()[0] == 0:
            self._start_polling(id)
        return 0, "播放成功"

    def _update_index_and_play(self, id: str, new_index: int) -> tuple[int, str]:
        playlist_data, code, msg = self._validate_playlist(id)
        if code != 0:
            return code, msg

        files = playlist_data.get("files", [])
        playlist_data["current_index"] = new_index % len(files)
        playlist_data["updated_time"] = _TS()
        rds_mgr.set(PLAYLIST_RDS_FULL_KEY, json.dumps(self.playlist_raw, ensure_ascii=False))

        code, msg = self.play(id)
        return (0, "播放成功") if code == 0 else (-1, msg)

    def play_next(self, id: str) -> tuple[int, str]:
        playlist_data, code, msg = self._validate_playlist(id)
        if code != 0:
            return code, msg
        current_index = playlist_data.get("current_index", 0)
        return self._update_index_and_play(id, current_index + 1)

    def play_pre(self, id: str) -> tuple[int, str]:
        playlist_data, code, msg = self._validate_playlist(id)
        if code != 0:
            return code, msg
        current_index = playlist_data.get("current_index", 0)
        return self._update_index_and_play(id, current_index - 1)

    def stop(self, id: str) -> tuple[int, str]:
        if not self.playlist_raw or id not in self.playlist_raw:
            return -1, "播放列表不存在"

        device_obj = self.device_map.get(id)
        if device_obj is None:
            return -1, "设备不存在或未初始化"

        # 停止轮询
        self._stop_polling(id)

        # 清除定时任务触发的播放开始时间记录
        if id in self._scheduled_play_start_times:
            del self._scheduled_play_start_times[id]

        # 停止播放
        return device_obj["obj"].stop()

    def _start_polling(self, id: str):
        if id in self._polling_playlists:
            return
        device_obj = self.device_map.get(id)
        if device_obj is None:
            return
        device = device_obj["obj"]
        if device is None:
            return
        if device.get_transport_info()[0] != 0:
            return

        def poll_task():
            if id not in self._polling_playlists:
                return
            code, msg = self._check_and_auto_play_next(id)
            if code == 0:
                log.info(f"[PlaylistMgr] 自动播放下一首成功: {id}")

        scheduler = get_scheduler()
        scheduler.add_interval_job(func=poll_task, job_id=f"playlist_poll_{id}", seconds=self._polling_interval)
        self._polling_playlists.add(id)
        log.info(f"[PlaylistMgr] 启动播放列表轮询任务: {id}, 间隔: {self._polling_interval}秒")

    def _stop_polling(self, id: str):
        if id not in self._polling_playlists:
            return
        scheduler = get_scheduler()
        scheduler.remove_job(f"playlist_poll_{id}")
        self._polling_playlists.discard(id)
        log.info(f"[PlaylistMgr] 停止播放列表轮询任务: {id}")

    def _check_and_auto_play_next(self, id: str) -> tuple[int, str]:
        if not self.playlist_raw or id not in self.playlist_raw:
            return -1, "播放列表不存在"
        playlist_data = self.playlist_raw[id]
        device_obj = self.device_map.get(id)
        if device_obj is None:
            return -1, "设备不存在或未初始化"
        device = device_obj["obj"]
        if device is None:
            return -1, "设备对象未初始化"

        if id in self._scheduled_play_start_times:
            schedule = playlist_data.get("schedule", {})
            duration_minutes = schedule.get("duration", 0)
            if duration_minutes > 0:
                elapsed_minutes = (datetime.datetime.now() - self._scheduled_play_start_times[id]).total_seconds() / 60
                if elapsed_minutes >= duration_minutes:
                    log.info(f"[PlaylistMgr] 定时任务播放时长限制到达 ({elapsed_minutes:.1f}分钟 >= {duration_minutes}分钟)，停止播放: {id}")
                    del self._scheduled_play_start_times[id]
                    code, msg = self.stop(id)
                    return (0, "播放时长限制到达，已停止播放") if code == 0 else (code, msg)

        pos_code, pos_info = device.get_position_info()
        if pos_code != 0:
            return -1, "无法获取播放位置信息"

        def time_to_seconds(time_str):
            parts = time_str.split(':')
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]) if len(parts) == 3 else 0

        try:
            duration_sec = time_to_seconds(pos_info.get("track_duration", "00:00:00"))
            rel_sec = time_to_seconds(pos_info.get("rel_time", "00:00:00"))
            if duration_sec <= 0:
                return -1, "无法获取有效的曲目时长"
            if rel_sec >= duration_sec or rel_sec >= duration_sec - 1:
                return self.play_next(id)
        except Exception as e:
            log.warning(f"[PlaylistMgr] Error checking playback completion: {e}")
        return -1, "播放未完成"


playlist_mgr = PlaylistMgr()
