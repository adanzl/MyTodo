import datetime
import json
import os
import sys
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union

from core.utils import get_media_duration
from core.db import rds_mgr
from core.device.agent import DeviceAgent
from core.device.bluetooth import BluetoothDev
from core.device.dlna import DlnaDev
from core.device.mi_device import MiDevice
from core.log_config import root_logger
from core.scheduler import get_scheduler
from core.utils import time_to_seconds

log = root_logger()

PLAYLIST_RDS_FULL_KEY = "schedule_play:playlist_collection"
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
        self._play_state = {}  # 播放状态跟踪 {playlist_id: {'in_pre_files': bool, 'pre_index': int, 'file_index': int}}
        self.reload()

    def get_playlist(self, id: str | None = None) -> Dict[str, Dict[str, Any]]:
        """
        获取播放列表
        :param id: 播放列表ID，如果为None则返回所有播放列表
        :return: 播放列表字典，格式为 {playlist_id: playlist_data}
                 如果id为None，返回所有播放列表；如果id有值，返回只包含该播放列表的字典；如果不存在则返回空字典
                 如果播放列表中有 isPlaying 字段，表示正在播放
        """
        if id is None:
            return self.playlist_raw
        playlist_data = self.playlist_raw.get(id)
        if playlist_data is None:
            return {}
        return {id: playlist_data}

    def _save_playlist_to_rds(self):
        """保存播放列表到 RDS"""
        rds_mgr.set(PLAYLIST_RDS_FULL_KEY, json.dumps(self.playlist_raw, ensure_ascii=False))

    def save_playlist(self, collection: Dict[str, Any]) -> int:
        self.playlist_raw = collection
        self._save_playlist_to_rds()
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
        """清理孤立的定时任务和状态"""
        scheduler = get_scheduler()
        playlist_ids = set(self.playlist_raw.keys() if self.playlist_raw else [])

        # 清理孤立的定时任务
        job_prefixes = [("playlist_cron_", "定时任务"), ("playlist_file_timer_", "文件定时器"),
                        ("playlist_duration_timer_", "播放列表时长定时器")]
        for job in scheduler.get_all_jobs():
            for prefix, name in job_prefixes:
                if job.id.startswith(prefix):
                    playlist_id = job.id.replace(prefix, "", 1)
                    if playlist_id not in playlist_ids:
                        scheduler.remove_job(job.id)
                        log.info(f"[PlaylistMgr] 清理孤立的{name}: {job.id}")
                    break

        # 清理孤立的状态记录
        state_dicts = [(self._scheduled_play_start_times, "定时任务播放开始时间"), (self._file_timers, "文件定时器"),
                       (self._playlist_duration_timers, "播放列表时长定时器"), (self._play_state, "播放状态跟踪")]
        for state_dict, name in state_dicts:
            for playlist_id in list(state_dict.keys()):
                if playlist_id not in playlist_ids:
                    del state_dict[playlist_id]

        # 清理孤立的播放状态记录
        self._playing_playlists &= playlist_ids

    def _update_file_duration(self, file_path: str, file_item: Any) -> Optional[int]:
        """更新当前播放文件的时长"""
        if not file_path:
            return None

        duration = get_media_duration(file_path)
        if duration is None:
            return None

        file_duration_seconds = int(duration)
        # 更新时长（file_item 是列表中的引用，直接修改即可）
        file_item["duration"] = file_duration_seconds
        self._save_playlist_to_rds()        
        return file_duration_seconds

    def _validate_playlist(self, id: str):
        """验证播放列表是否存在且有效"""
        if not self.playlist_raw or id not in self.playlist_raw:
            return None, -1, "播放列表不存在"
        playlist_data = self.playlist_raw[id]
        pre_files, files = playlist_data.get("pre_files", []), playlist_data.get("files", [])
        if not files and not pre_files:
            return None, -1, "播放列表为空"
        device_obj = self.device_map.get(id)
        if device_obj is None:
            return None, -1, "设备不存在或未初始化"
        return playlist_data, 0, None

    def _init_play_state(self, id: str, playlist_data: Dict[str, Any], pre_files: List):
        """初始化播放状态"""
        current_index = playlist_data.get("current_index", 0)
        if pre_files:
            self._play_state[id] = {"in_pre_files": True, "pre_index": 0, "file_index": current_index}
        else:
            self._play_state[id] = {"in_pre_files": False, "pre_index": 0, "file_index": current_index}

    def _get_current_file(self, play_state: Dict[str, Any], pre_files: List, files: List) -> tuple[Any, str]:
        """获取当前要播放的文件"""
        if play_state["in_pre_files"]:
            pre_index = play_state["pre_index"]
            if pre_index < 0 or pre_index >= len(pre_files):
                return None, f"pre_files 索引 {pre_index} 超出范围"
            return pre_files[pre_index], None
        else:
            file_index = play_state["file_index"]
            if file_index < 0 or file_index >= len(files):
                return None, f"files 索引 {file_index} 超出范围"
            return files[file_index], None

    def _cleanup_play_state(self, id: str):
        """清理播放状态"""
        self._clear_timer(id, self._file_timers, "playlist_file_timer_")
        self._clear_timer(id, self._playlist_duration_timers, "playlist_duration_timer_")
        self._scheduled_play_start_times.pop(id, None)
        self._playing_playlists.discard(id)
        self._play_state.pop(id, None)
        playlist_data = self.playlist_raw.get(id)
        if playlist_data and 'isPlaying' in playlist_data:
            del playlist_data['isPlaying']

    def play(self, id: str, force: bool = False) -> tuple[int, str]:
        """
        播放播放列表
        播放逻辑：先从头播放 pre_files 中的所有文件，然后播放 files 中从 current_index 开始的文件
        :param id: 播放列表ID
        :param force: 是否强制播放（即使正在播放也继续）
        :return: (错误码, 消息)
        """
        if not force and id in self._playing_playlists:
            return -1, "播放列表正在播放中，请勿重复播放"

        playlist_data, code, msg = self._validate_playlist(id)
        if code != 0:
            return code, msg

        pre_files, files = playlist_data.get("pre_files", []), playlist_data.get("files", [])

        # 如果不是 force 模式或没有播放状态，初始化播放状态
        if not force or id not in self._play_state:
            self._init_play_state(id, playlist_data, pre_files)

        play_state = self._play_state[id]
        file_item, error_msg = self._get_current_file(play_state, pre_files, files)
        if error_msg:
            return -1, error_msg

        file_path = _get_file_uri(file_item)
        if not file_path:
            return -1, "文件路径无效"

        # 获取并更新文件时长
        file_duration_seconds = self._update_file_duration(file_path, file_item)

        # 播放文件
        device = self.device_map[id]["obj"]
        code, msg = device.play(file_path)
        if code != 0:
            return code, msg

        # 标记为正在播放
        self._playing_playlists.add(id)
        playlist_data['isPlaying'] = True
        self._clear_timer(id, self._file_timers, "playlist_file_timer_")

        # 启动文件定时器
        if file_duration_seconds and file_duration_seconds > 0:
            self._start_file_timer(id, file_duration_seconds)

        # 启动播放列表时长限制定时器
        schedule = playlist_data.get("schedule", {})
        playlist_duration_minutes = schedule.get("duration", 0)
        if playlist_duration_minutes > 0 and id not in self._playlist_duration_timers:
            self._start_playlist_duration_timer(id, playlist_duration_minutes)
            self._scheduled_play_start_times[id] = datetime.datetime.now()

        return 0, "播放成功"

    def _update_index_and_play(self, id: str, in_pre_files: bool = None, pre_index: int = None,
                               file_index: int = None) -> tuple[int, str]:
        """更新播放索引并播放"""
        playlist_data, code, msg = self._validate_playlist(id)
        if code != 0:
            return code, msg

        pre_files, files = playlist_data.get("pre_files", []), playlist_data.get("files", [])

        # 初始化播放状态（如果不存在）
        if id not in self._play_state:
            self._init_play_state(id, playlist_data, pre_files)

        play_state = self._play_state[id]

        # 更新状态
        if in_pre_files is not None:
            play_state["in_pre_files"] = in_pre_files
        if pre_index is not None:
            play_state["pre_index"] = pre_index
        if file_index is not None:
            play_state["file_index"] = file_index

        # 更新播放列表的 current_index（只对 files 生效）
        if not play_state["in_pre_files"] and files:
            playlist_data["current_index"] = play_state["file_index"]
            playlist_data["updated_time"] = _TS()
            self._save_playlist_to_rds()

        return self.play(id, force=True)

    def play_next(self, id: str) -> tuple[int, str]:
        """播放下一首"""
        playlist_data, code, msg = self._validate_playlist(id)
        if code != 0:
            return code, msg

        pre_files, files = playlist_data.get("pre_files", []), playlist_data.get("files", [])

        # 如果没有播放状态，初始化并从头开始
        if id not in self._play_state:
            if pre_files:
                return self._update_index_and_play(id, in_pre_files=True, pre_index=0,
                                                   file_index=playlist_data.get("current_index", 0))
            return self._update_index_and_play(id, file_index=playlist_data.get("current_index", 0))

        play_state = self._play_state[id]

        if play_state["in_pre_files"]:
            # 播放 pre_files 的下一首
            next_pre_index = play_state["pre_index"] + 1
            if next_pre_index < len(pre_files):
                return self._update_index_and_play(id, in_pre_files=True, pre_index=next_pre_index,
                                                   file_index=play_state["file_index"])
            # pre_files 播放完了，开始播放 files
            if files and play_state["file_index"] < len(files):
                return self._update_index_and_play(id, in_pre_files=False, file_index=play_state["file_index"])
            return -1, "没有更多文件可播放"
        else:
            # 播放 files 的下一首
            next_file_index = play_state["file_index"] + 1
            if next_file_index < len(files):
                return self._update_index_and_play(id, file_index=next_file_index)
            return -1, "没有更多文件可播放"

    def play_pre(self, id: str) -> tuple[int, str]:
        """播放上一首"""
        playlist_data, code, msg = self._validate_playlist(id)
        if code != 0:
            return code, msg

        pre_files, files = playlist_data.get("pre_files", []), playlist_data.get("files", [])

        # 如果没有播放状态，初始化
        if id not in self._play_state:
            if pre_files:
                return self._update_index_and_play(id, in_pre_files=True, pre_index=len(pre_files) - 1,
                                                   file_index=playlist_data.get("current_index", 0))
            current_index = playlist_data.get("current_index", 0)
            prev_index = (current_index - 1) % len(files) if files else 0
            return self._update_index_and_play(id, file_index=prev_index)

        play_state = self._play_state[id]

        if play_state["in_pre_files"]:
            # 播放 pre_files 的上一首
            prev_pre_index = play_state["pre_index"] - 1
            if prev_pre_index >= 0:
                return self._update_index_and_play(id, in_pre_files=True, pre_index=prev_pre_index,
                                                   file_index=play_state["file_index"])
            return -1, "已经是第一首"
        else:
            # 播放 files 的上一首
            prev_file_index = play_state["file_index"] - 1
            if prev_file_index >= 0:
                return self._update_index_and_play(id, file_index=prev_file_index)
            # files 在开头，回到 pre_files 的最后
            if pre_files:
                return self._update_index_and_play(id, in_pre_files=True, pre_index=len(pre_files) - 1, file_index=0)
            return -1, "已经是第一首"

    def stop(self, id: str) -> tuple[int, str]:
        """停止播放"""
        playlist_data, code, msg = self._validate_playlist(id)
        if code != 0:
            return code, msg

        device_obj = self.device_map.get(id)
        if device_obj is None:
            return -1, "设备不存在或未初始化"

        # 清理所有播放状态
        self._cleanup_play_state(id)

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
            self._clear_timer(pid, self._file_timers, "playlist_file_timer_")
            self.play_next(pid)

        # 使用 DateTrigger 在指定时间后执行
        run_date = datetime.datetime.now() + timedelta(seconds=duration_seconds)
        scheduler.add_date_job(func=__play_next_task, job_id=job_id, run_date=run_date)
        self._file_timers[id] = job_id
        log.info(f"[PlaylistMgr] 启动文件定时器: {id}, 将在 {duration_seconds} 秒后播放下一首")

    def _clear_timer(self, id: str, timer_dict: Dict[str, str], job_prefix: str):
        """清除定时器"""
        if id in timer_dict:
            scheduler = get_scheduler()
            job_id = timer_dict[id]
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
            del timer_dict[id]

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
            self._clear_timer(pid, self._playlist_duration_timers, "playlist_duration_timer_")
            self._scheduled_play_start_times.pop(pid, None)
            self.stop(pid)

        # 使用 DateTrigger 在指定时间后执行
        run_date = datetime.datetime.now() + timedelta(minutes=duration_minutes)
        scheduler.add_date_job(func=stop_playlist_task, job_id=job_id, run_date=run_date)
        self._playlist_duration_timers[id] = job_id
        log.info(f"[PlaylistMgr] 启动播放列表时长定时器: {id}, 将在 {duration_minutes} 分钟后停止播放")


playlist_mgr = PlaylistMgr()
