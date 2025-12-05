import datetime
import json
import os
import sys
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional

from core.api.routes import get_media_duration
from core.db import rds_mgr
from core.device.agent import DeviceAgent
from core.device.bluetooth import BluetoothDev
from core.device.dlna import DlnaDev
from core.device.mi_device import MiDevice
from core.log_config import root_logger
from core.scheduler import get_scheduler
from core.utils import time_to_seconds

log = root_logger()

PLAYLIST_RDS_FULL_KEY = f"schedule_play:playlist_collection"
DEFAULT_PLAYLIST_NAME = "默认播放列表"
DEVICE_TYPES = {"device_agent", "bluetooth", "dlna", "mi"}

_TS = lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _create_device(node):
    ret = {"node": node, "obj": None}
    if node["type"] == "agent":
        ret["obj"] = DeviceAgent(node["address"])
    elif node["type"] == "bluetooth":
        ret["obj"] = BluetoothDev(node["address"])
    elif node["type"] == "dlna":
        ret["obj"] = DlnaDev(node["address"])
    elif node["type"] == "mi":
        ret["obj"] = MiDevice(node.get("address", ""))
    return ret


def _get_file_uri(file_item):
    if isinstance(file_item, str):
        return file_item
    if isinstance(file_item, dict):
        return file_item.get("uri") or file_item.get("path") or file_item.get("file") or ""
    return ""


class PlaylistMgr:

    def __init__(self):
        self._scheduled_play_start_times = {}  # 定时任务播放开始时间（用于duration限制）
        self._file_timers = {}  # 文件播放定时器 {playlist_id: job_id}
        self._playlist_duration_timers = {}  # 播放列表时长定时器 {playlist_id: job_id}
        self._playing_playlists = set()  # 正在播放的播放列表ID集合
        self.playlist_raw = {}  # 播放列表数据
        self.device_map = {}  # 设备映射
        self.reload()

    def get_playlist(self, id: str) -> Dict[str, Any] | None:
        return self.playlist_raw.get(id, None)

    def save_playlist(self, collection: Dict[str, Any]) -> int:
        rds_mgr.set(PLAYLIST_RDS_FULL_KEY, json.dumps(collection, ensure_ascii=False))
        self.playlist_raw = collection
        # 更新设备映射
        self._refresh_device_map()
        return 0

    def reload(self) -> int:
        if sys.platform != "linux":
            log.warning(f"[PlaylistMgr] Reload not supported on non-linux platforms : {sys.platform}")
            # 确保 playlist_raw 和 device_map 已初始化
            if not hasattr(self, 'playlist_raw'):
                self.playlist_raw = {}
            if not hasattr(self, 'device_map'):
                self.device_map = {}
            return 0
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
        if self.playlist_raw and sys.platform == "linux":
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
            try:
                # 定时任务使用 force=True 允许播放（即使正在播放也继续）
                code, msg = self.play(pid, force=True)
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
            elif job.id.startswith("playlist_file_timer_"):
                playlist_id = job.id.replace("playlist_file_timer_", "", 1)
                if playlist_id not in playlist_ids:
                    scheduler.remove_job(job.id)
                    log.info(f"[PlaylistMgr] 清理孤立的文件定时器: {job.id}")
            elif job.id.startswith("playlist_duration_timer_"):
                playlist_id = job.id.replace("playlist_duration_timer_", "", 1)
                if playlist_id not in playlist_ids:
                    scheduler.remove_job(job.id)
                    log.info(f"[PlaylistMgr] 清理孤立的播放列表时长定时器: {job.id}")

        for playlist_id in list(self._scheduled_play_start_times.keys()):
            if playlist_id not in playlist_ids:
                del self._scheduled_play_start_times[playlist_id]

        # 清理孤立的定时器记录
        for playlist_id in list(self._file_timers.keys()):
            if playlist_id not in playlist_ids:
                del self._file_timers[playlist_id]

        for playlist_id in list(self._playlist_duration_timers.keys()):
            if playlist_id not in playlist_ids:
                del self._playlist_duration_timers[playlist_id]
        
        # 清理孤立的播放状态记录
        self._playing_playlists &= playlist_ids

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

    def play(self, id: str, force: bool = False) -> tuple[int, str]:
        """
        播放播放列表
        :param id: 播放列表ID
        :param force: 是否强制播放（即使正在播放也继续）
        :return: (错误码, 消息)
        """
        # 检查是否正在播放，防止重复播放
        if not force and id in self._playing_playlists:
            return -1, "播放列表正在播放中，请勿重复播放"
        
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
        file_duration_seconds = None
        if duration is not None:
            # 更新当前播放文件的时长
            files[current_index]["duration"] = duration
            # 如果 duration 是秒数，直接使用；如果是字符串格式，转换为秒数
            if isinstance(duration, (int, float)):
                file_duration_seconds = duration
            elif isinstance(duration, str):
                file_duration_seconds = time_to_seconds(duration)

        device = self.device_map[id]["obj"]
        code, msg = device.play(file_path)
        if code != 0:
            return code, msg

        # 标记为正在播放
        self._playing_playlists.add(id)

        # 清除之前的文件定时器
        self._clear_file_timer(id)

        # 如果获取到了文件时长，启动定时器自动播放下一首
        if file_duration_seconds and file_duration_seconds > 0:
            self._start_file_timer(id, file_duration_seconds)

        # 检查是否需要启动播放列表时长限制定时器
        schedule = playlist_data.get("schedule", {})
        playlist_duration_minutes = schedule.get("duration", 0)
        if playlist_duration_minutes > 0:
            # 如果还没有启动播放列表时长定时器，则启动
            if id not in self._playlist_duration_timers:
                self._start_playlist_duration_timer(id, playlist_duration_minutes)
                self._scheduled_play_start_times[id] = datetime.datetime.now()

        return 0, "播放成功"

    def _update_index_and_play(self, id: str, new_index: int) -> tuple[int, str]:
        playlist_data, code, msg = self._validate_playlist(id)
        if code != 0:
            return code, msg

        files = playlist_data.get("files", [])
        playlist_data["current_index"] = new_index % len(files)
        playlist_data["updated_time"] = _TS()
        rds_mgr.set(PLAYLIST_RDS_FULL_KEY, json.dumps(self.playlist_raw, ensure_ascii=False))

        # 使用 force=True 允许切换播放（因为已经在播放中）
        code, msg = self.play(id, force=True)
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

        # 清除文件定时器
        self._clear_file_timer(id)

        # 清除播放列表时长定时器
        self._clear_playlist_duration_timer(id)

        # 清除定时任务触发的播放开始时间记录
        if id in self._scheduled_play_start_times:
            del self._scheduled_play_start_times[id]

        # 清除播放状态
        self._playing_playlists.discard(id)

        # 停止播放
        return device_obj["obj"].stop()

    def _start_file_timer(self, id: str, duration_seconds: float):
        """
        启动文件播放定时器，在文件播放完成后自动播放下一首
        :param id: 播放列表ID
        :param duration_seconds: 文件时长（秒）
        """
        scheduler = get_scheduler()
        job_id = f"playlist_file_timer_{id}"

        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        def __play_next_task(pid=id):
            """定时器触发时，判断position，如果比duration小超过2s则等一下差值"""
            device = self.device_map.get(pid, {}).get("obj")
            if device:
                try:
                    code, status = device.get_status()
                    if code == 0:
                        wait_seconds = time_to_seconds(status.get("duration", "00:00:00")) - \
                                     time_to_seconds(status.get("position", "00:00:00"))
                        if wait_seconds >= 2:
                            time.sleep(wait_seconds)
                except Exception as e:
                    log.error(f"[PlaylistMgr] 检查播放状态异常: {pid}, {e}")
            self._clear_file_timer(pid)
            self.play_next(pid)

        # 使用 DateTrigger 在指定时间后执行
        run_date = datetime.datetime.now() + timedelta(seconds=duration_seconds)
        scheduler.add_date_job(func=__play_next_task, job_id=job_id, run_date=run_date)
        self._file_timers[id] = job_id
        log.info(f"[PlaylistMgr] 启动文件定时器: {id}, 将在 {duration_seconds} 秒后播放下一首")

    def _clear_file_timer(self, id: str):
        """清除文件播放定时器"""
        if id in self._file_timers:
            scheduler = get_scheduler()
            if scheduler.get_job(self._file_timers[id]):
                scheduler.remove_job(self._file_timers[id])
            del self._file_timers[id]

    def _start_playlist_duration_timer(self, id: str, duration_minutes: int):
        """
        启动播放列表时长限制定时器，在指定时长后停止播放列表
        :param id: 播放列表ID
        :param duration_minutes: 播放时长限制（分钟）
        """
        scheduler = get_scheduler()
        job_id = f"playlist_duration_timer_{id}"

        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        def stop_playlist_task(pid=id):
            self._clear_playlist_duration_timer(pid)
            self._scheduled_play_start_times.pop(pid, None)
            self.stop(pid)

        # 使用 DateTrigger 在指定时间后执行
        run_date = datetime.datetime.now() + timedelta(minutes=duration_minutes)
        scheduler.add_date_job(func=stop_playlist_task, job_id=job_id, run_date=run_date)
        self._playlist_duration_timers[id] = job_id
        log.info(f"[PlaylistMgr] 启动播放列表时长定时器: {id}, 将在 {duration_minutes} 分钟后停止播放")

    def _clear_playlist_duration_timer(self, id: str):
        """清除播放列表时长定时器"""
        if id in self._playlist_duration_timers:
            scheduler = get_scheduler()
            if scheduler.get_job(self._playlist_duration_timers[id]):
                scheduler.remove_job(self._playlist_duration_timers[id])
            del self._playlist_duration_timers[id]


playlist_mgr = PlaylistMgr()
