import datetime
import json
import os
import sys
import time
import threading
from datetime import timedelta
from typing import Any, Counter, Dict, List, Optional

from core.utils import get_media_duration, check_cron_will_trigger_today
from core.db import rds_mgr
from core.device.agent import DeviceAgent
from core.device.bluetooth import BluetoothDev
from core.device.dlna import DlnaDev
from core.device.mi_device import MiDevice
from core.log_config import root_logger
from core.services.scheduler_mgr import scheduler_mgr
from core.utils import time_to_seconds

log = root_logger()

PLAYLIST_RDS_FULL_KEY = "schedule_play:playlist_collection"
DEFAULT_PLAYLIST_NAME = "默认播放列表"
DEVICE_TYPES = {"device_agent", "bluetooth", "dlna", "mi"}

_TS = lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _create_device(node):
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


def _get_file_uri(file_item):
    return file_item.get("uri") or file_item.get("path") or file_item.get("file") or ""


class PlaylistMgr:

    def __init__(self):
        self._scheduled_play_start_times = {}  # 定时任务播放开始时间（用于duration限制）
        self._file_timers = {}  # 文件播放定时器 {playlist_id: job_id}
        self._playlist_duration_timers = {}  # 播放列表时长定时器 {playlist_id: job_id}
        self._playing_playlists = set()  # 正在播放的播放列表ID集合
        self._playlist_raw = {}  # 播放列表数据
        self._device_map = {}  # 设备映射
        self._play_state = {}  # 播放状态跟踪 {playlist_id: {'in_pre_files': bool, 'pre_index': int, 'file_index': int}}
        self._duration_fetch_thread = None  # 批量获取时长的单例线程
        self._duration_fetch_lock = threading.Lock()  # 线程锁
        self._duration_blacklist = Counter()  # 获取时长失败的黑名单 {file_uri: failure_count}
        self._needs_reload = False  # 标记是否需要重新从 RDS 加载
        self.reload()

    def get_playlist(self, id: str | None = None) -> Dict[str, Dict[str, Any]]:
        """
        获取播放列表
        :param id: 播放列表ID，如果为None则返回所有播放列表
        :return: 播放列表字典，格式为 {playlist_id: playlist_data}
                 如果id为None，返回所有播放列表；如果id有值，返回只包含该播放列表的字典；如果不存在则返回空字典
                 如果播放列表中有 isPlaying 字段，表示正在播放
        """
        # 如果需要重新加载，再次尝试加载
        if self._needs_reload:
            log.info(f"[PlaylistMgr] 需要重新加载，再次尝试从 RDS 加载")
            self.reload()

        if id is None:
            result = self._playlist_raw
        else:
            playlist_data = self._playlist_raw.get(id)
            if playlist_data is None:
                return {}
            result = {id: playlist_data}

        # 汇总所有没有 duration 的文件，启动单例线程批量获取时长
        self._start_batch_duration_fetch(result)

        return result

    def _save_playlist_to_rds(self):
        """保存播放列表到 RDS"""
        rds_mgr.set(PLAYLIST_RDS_FULL_KEY, json.dumps(self._playlist_raw, ensure_ascii=False))

    def save_playlist(self, collection: Dict[str, Any]) -> int:
        self._playlist_raw = collection
        self._save_playlist_to_rds()
        # 更新设备映射
        self._refresh_device_map()
        return 0

    def reload(self) -> int:
        if sys.platform != "linux":
            log.warning(f"[PlaylistMgr] Reload not supported on non-linux platforms : {sys.platform}")
            # 确保 playlist_raw 和 device_map 已初始化
            if not hasattr(self, 'playlist_raw'):
                self._playlist_raw = {}
            if not hasattr(self, 'device_map'):
                self._device_map = {}
            self._needs_reload = False
            return 0
        """
        重新从 RDS 中加载 playlist 数据
        """
        try:
            raw = rds_mgr.get(PLAYLIST_RDS_FULL_KEY)
            if raw:
                self._playlist_raw = json.loads(raw.decode("utf-8"))
            else:
                self._playlist_raw = {}
            self._refresh_device_map()
            self._needs_reload = False
            log.info(f"[PlaylistMgr] Load success: {len(self._playlist_raw)} playlists")
            return 0
        except Exception as e:
            log.error(f"[PlaylistMgr] Reload error: {e}")
            self._needs_reload = True
            return -1

    
    def _refresh_device_map(self):
        self._device_map = {}
        if self._playlist_raw and sys.platform == "linux":
            for p_id in self._playlist_raw:
                playlist_data = self._playlist_raw[p_id]
                self._device_map[p_id] = _create_device(playlist_data.get("device", {}))
                self._refresh_cron_job(p_id, playlist_data)
        self._cleanup_orphaned_cron_jobs()

    def _refresh_cron_job(self, playlist_id: str, playlist_data: Dict[str, Any]):
        scheduler = scheduler_mgr
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
                p_name = self._playlist_raw.get(pid, {}).get("name", "未知播放列表")
                # 检查播放列表是否正在播放中，如果正在播放则跳过定时任务
                if pid in self._playing_playlists:
                    log.info(f"[PlaylistMgr] 定时任务触发时播放列表正在播放中，跳过播放任务: {pid} - {p_name}")
                    return
                
                # 如果不在播放中，正常启动播放
                code, msg = self.play(pid, force=False)
                if code == 0:
                    self._scheduled_play_start_times[pid] = datetime.datetime.now()
                    log.info(f"[PlaylistMgr] 定时任务播放成功: {pid} - {p_name}")
                else:
                    log.error(f"[PlaylistMgr] 定时任务播放失败: {pid} - {p_name}, {msg}")
            except Exception as e:
                log.error(f"[PlaylistMgr] 定时任务执行异常: {pid} - {p_name}, {e}")

        success = scheduler.add_cron_job(func=cron_play_task, job_id=job_id, cron_expression=cron_expression)
        playlist_name = playlist_data.get("name", "未知播放列表")
        if success:
            log.info(f"[PlaylistMgr] 创建定时任务成功: {playlist_id}, {playlist_name}, cron: {cron_expression}")
        else:
            log.error(f"[PlaylistMgr] 创建定时任务失败: {playlist_id}, {playlist_name}, cron: {cron_expression}")

    def _cleanup_orphaned_cron_jobs(self):
        """清理孤立的定时任务和状态"""
        scheduler = scheduler_mgr
        playlist_ids = set(self._playlist_raw.keys() if self._playlist_raw else [])

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

    def _start_batch_duration_fetch(self, playlists: Dict[str, Dict[str, Any]]):
        """
        汇总所有没有 duration 的文件，启动单例线程批量获取时长
        :param playlists: 播放列表字典
        """
        # 检查是否有正在运行的线程
        with self._duration_fetch_lock:
            if self._duration_fetch_thread is not None and self._duration_fetch_thread.is_alive():
                log.debug("[PlaylistMgr] 批量获取时长的线程正在运行，跳过本次启动")
                return

        # 收集所有没有 duration 的文件 URI（去重），排除黑名单中失败超过3次的文件
        files_to_fetch = set()  # {file_uri, ...}
        for playlist_data in playlists.values():
            # 检查 pre_files
            for file_item in playlist_data.get("pre_files", []):
                if not file_item.get("duration"):
                    file_uri = _get_file_uri(file_item)
                    if file_uri:
                        # 检查黑名单，失败次数>=3则跳过
                        failure_count = self._duration_blacklist.get(file_uri, 0)
                        if failure_count < 3:
                            files_to_fetch.add(file_uri)

            # 检查 files/playlist
            for file_item in playlist_data.get("files", []):
                if not file_item.get("duration"):
                    file_uri = _get_file_uri(file_item)
                    if file_uri:
                        # 检查黑名单，失败次数>=3则跳过
                        failure_count = self._duration_blacklist.get(file_uri, 0)
                        if failure_count < 3:
                            files_to_fetch.add(file_uri)

        if not files_to_fetch:
            return

        log.info(f"[PlaylistMgr] 发现 {len(files_to_fetch)} 个文件需要获取时长，启动批量获取线程")

        def _batch_fetch_durations():
            """批量获取文件时长的线程函数"""
            file_durations = {}  # {file_uri: duration_seconds, ...}
            failed_count = 0
            failed_uris = []
            try:
                for file_uri in files_to_fetch:
                    try:
                        duration = get_media_duration(file_uri)
                        file_durations[file_uri] = int(duration)
                        # 成功获取，从黑名单中移除（如果存在）
                        self._duration_blacklist.pop(file_uri, None)
                    except Exception as e:
                        failed_count += 1
                        failed_uris.append(file_uri)
                        # 获取异常，更新黑名单
                        self._duration_blacklist[file_uri] += 1

                # 反向更新所有播放列表中匹配的文件 duration
                updated_count = 0
                for _, playlist_data in self._playlist_raw.items():
                    # 更新 pre_files
                    pre_files = playlist_data.get("pre_files", [])
                    for file_item in pre_files:
                        file_uri = _get_file_uri(file_item)
                        if file_uri in file_durations and not file_item.get("duration"):
                            file_item["duration"] = file_durations[file_uri]
                            updated_count += 1

                    # 更新 files/playlist
                    files = playlist_data.get("files", [])
                    for file_item in files:
                        file_uri = _get_file_uri(file_item)
                        if file_uri in file_durations and not file_item.get("duration"):
                            file_item["duration"] = file_durations[file_uri]
                            updated_count += 1

                # 统一保存到 RDS
                if updated_count > 0:
                    self._save_playlist_to_rds()
                    log.info(f"[PlaylistMgr] 批量获取时长完成: 成功 {updated_count} 个, 失败 {failed_count} 个, 失败文件: {failed_uris}")
            except Exception as e:
                log.error(f"[PlaylistMgr] 批量获取时长线程异常: {e}")
            finally:
                # 清理线程引用
                with self._duration_fetch_lock:
                    self._duration_fetch_thread = None

        # 启动单例线程
        with self._duration_fetch_lock:
            if self._duration_fetch_thread is not None and self._duration_fetch_thread.is_alive():
                log.debug("[PlaylistMgr] 批量获取时长的线程正在运行，跳过本次启动")
                return

            self._duration_fetch_thread = threading.Thread(target=_batch_fetch_durations,
                                                           daemon=True,
                                                           name="PlaylistDurationFetcher")
            self._duration_fetch_thread.start()

    def _validate_playlist(self, id: str):
        """验证播放列表是否存在且有效"""
        if not self._playlist_raw or id not in self._playlist_raw:
            return None, -1, "播放列表不存在"
        playlist_data = self._playlist_raw[id]
        pre_files, files = playlist_data.get("pre_files", []), playlist_data.get("files", [])
        if not files and not pre_files:
            return None, -1, "播放列表为空"
        device_obj = self._device_map.get(id)
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
        playlist_data = self._playlist_raw.get(id)
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

        # 如果不是 force 模式，初始化播放状态（从头开始）
        # 如果是 force 模式，只有在状态不存在时才初始化（避免覆盖已更新的状态）
        if not force:
            self._init_play_state(id, playlist_data, pre_files)
        elif id not in self._play_state:
            # force 模式且状态不存在时才初始化
            self._init_play_state(id, playlist_data, pre_files)

        # 确保播放状态存在（防御性编程）
        if id not in self._play_state:
            self._init_play_state(id, playlist_data, pre_files)

        play_state = self._play_state[id]
        file_item, error_msg = self._get_current_file(play_state, pre_files, files)
        if error_msg:
            return -1, error_msg

        file_path = _get_file_uri(file_item)
        if not file_path:
            return -1, "文件路径无效"

        log.info(f"[PlaylistMgr] play: 准备播放文件, id={id}, force={force}, 播放状态={play_state}, 文件路径={file_path}")

        # 获取并更新文件时长
        file_duration_seconds = self._update_file_duration(file_path, file_item)

        # 播放文件
        device = self._device_map[id]["obj"]
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

    def _update_index_and_play(self,
                               id: str,
                               in_pre_files: bool = None,
                               pre_index: int = None,
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
            log.info(f"[PlaylistMgr] play_next: 播放状态不存在，初始化状态: {id}")
            if pre_files:
                return self._update_index_and_play(id,
                                                   in_pre_files=True,
                                                   pre_index=0,
                                                   file_index=playlist_data.get("current_index", 0))
            return self._update_index_and_play(id, file_index=playlist_data.get("current_index", 0))

        play_state = self._play_state[id]

        if play_state["in_pre_files"]:
            # 播放 pre_files 的下一首
            next_pre_index = play_state["pre_index"] + 1
            if next_pre_index < len(pre_files):
                return self._update_index_and_play(id,
                                                   in_pre_files=True,
                                                   pre_index=next_pre_index,
                                                   file_index=play_state["file_index"])
            # pre_files 播放完了，开始播放 files（从保存的 file_index 开始）
            if files and play_state["file_index"] < len(files):
                return self._update_index_and_play(id, in_pre_files=False, file_index=play_state["file_index"])
            return -1, "没有更多文件可播放"
        else:
            # 播放 files 的下一首（使用取余实现循环）
            if files:
                next_file_index = (play_state["file_index"] + 1) % len(files)
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
                return self._update_index_and_play(id,
                                                   in_pre_files=True,
                                                   pre_index=len(pre_files) - 1,
                                                   file_index=playlist_data.get("current_index", 0))
            current_index = playlist_data.get("current_index", 0)
            prev_index = (current_index - 1) % len(files) if files else 0
            return self._update_index_and_play(id, file_index=prev_index)

        play_state = self._play_state[id]

        if play_state["in_pre_files"]:
            # 播放 pre_files 的上一首
            prev_pre_index = play_state["pre_index"] - 1
            if prev_pre_index >= 0:
                return self._update_index_and_play(id,
                                                   in_pre_files=True,
                                                   pre_index=prev_pre_index,
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

        device_obj = self._device_map.get(id)
        if device_obj is None:
            return -1, "设备不存在或未初始化"

        # 清理所有播放状态
        self._cleanup_play_state(id)

        # 停止播放
        return device_obj["obj"].stop()

    def trigger_button(self, button: str, action: str) -> tuple[int, str]:
        """
        触发按钮操作
        :param button: 按钮编号（"1", "2", "3"）
        :param action: 操作类型（"play", "stop"）
        :return: (错误码, 消息)
        """
        log.info(f"[PlaylistMgr] 触发按钮: {button}, {action}")
        if action == "stop":
            # stop 操作：停止所有关联的列表播放（不需要检查 cron）
            matching_playlists = []
            for playlist_id, playlist_data in self._playlist_raw.items():
                if playlist_data.get("trigger_button") == button:
                    matching_playlists.append(playlist_id)
            
            if not matching_playlists:
                return -1, f"未找到触发按钮 {button} 对应的播放列表"
            
            # 停止所有匹配的播放列表
            stopped_count = 0
            errors = []
            for playlist_id in matching_playlists:
                # 只停止正在播放的列表
                if playlist_id in self._playing_playlists:
                    code, msg = self.stop(playlist_id)
                    if code == 0:
                        stopped_count += 1
                    else:
                        errors.append(f"{playlist_id}: {msg}")
            
            if stopped_count > 0:
                return 0, f"已停止 {stopped_count} 个播放列表"
            elif errors:
                return -1, f"停止失败: {', '.join(errors)}"
            else:
                return 0, "没有正在播放的列表需要停止"
        
        elif action == "play":
            # play 操作：需要检查 cron 是否今天会触发
            matching_playlists = []
            for playlist_id, playlist_data in self._playlist_raw.items():
                if playlist_data.get("trigger_button") == button:
                    schedule = playlist_data.get("schedule", {})
                    # 检查 cron 是否启用且今天会触发
                    if schedule.get("enabled") == 1 and schedule.get("cron"):
                        cron_expression = schedule.get("cron", "").strip()
                        if cron_expression and check_cron_will_trigger_today(cron_expression):
                            matching_playlists.append((playlist_id, playlist_data))
            
            if not matching_playlists:
                return -1, f"未找到触发按钮 {button} 对应的播放列表，或今天不会触发"
            
            # 选择第一个匹配的播放列表（今天会触发的第一条）
            target_playlist_id = matching_playlists[0][0]
            return self.play(target_playlist_id)
        
        else:
            return -1, f"不支持的操作: {action}"

    def _start_file_timer(self, id: str, duration_seconds: float):
        """
        启动文件播放定时器，在文件播放完成后自动播放下一首
        :param id: 播放列表ID
        :param duration_seconds: 文件时长（秒）
        """
        scheduler = scheduler_mgr
        job_id = f"playlist_file_timer_{id}"

        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        def __play_next_task(pid=id):
            """定时器触发时，判断position，如果比duration小超过2s则等一下差值"""
            log.info(f"[PlaylistMgr] 文件定时器触发: {pid}, 当前播放状态: {self._play_state.get(pid)}")
            device = self._device_map.get(pid, {}).get("obj")
            wait_seconds = 0
            if device:
                try:
                    code, status = device.get_status()
                    if code == 0:
                        wait_seconds = time_to_seconds(status.get("duration", "00:00:00")) - \
                                     time_to_seconds(status.get("position", "00:00:00"))
                        log.info(f"[PlaylistMgr] 文件定时器触发时播放状态检查: {pid}, 剩余时长: {wait_seconds} 秒, 状态: {status}")
                        if wait_seconds >= 2:
                            log.info(f"[PlaylistMgr] 文件定时器触发，但播放尚未完成，等待 {wait_seconds} 秒: {pid}")
                            time.sleep(wait_seconds)
                except Exception as e:
                    log.error(f"[PlaylistMgr] 检查播放状态异常: {pid}, {e}")
            # 清除定时器（避免重复触发）
            self._clear_timer(pid, self._file_timers, "playlist_file_timer_")
            # 确保播放状态存在，如果不存在则初始化
            if pid not in self._play_state:
                log.warning(f"[PlaylistMgr] 文件定时器触发时播放状态丢失: {pid}，重新初始化")
                playlist_data = self._playlist_raw.get(pid)
                if playlist_data:
                    pre_files = playlist_data.get("pre_files", [])
                    self._init_play_state(pid, playlist_data, pre_files)
            log.info(f"[PlaylistMgr] 文件定时器触发，准备播放下一首: {pid}, 当前播放状态: {self._play_state.get(pid)}, 等待后剩余时长: {wait_seconds} 秒")
            # 播放下一首
            result = self.play_next(pid)
            # 如果播放失败，记录错误但不抛出异常（避免影响定时器）
            if result[0] != 0:
                log.warning(f"[PlaylistMgr] 定时器触发播放下一首失败: {pid}, {result[1]}")

        # 使用 DateTrigger 在指定时间后执行
        run_date = datetime.datetime.now() + timedelta(seconds=duration_seconds)
        scheduler.add_date_job(func=__play_next_task, job_id=job_id, run_date=run_date)
        self._file_timers[id] = job_id
        log.info(f"[PlaylistMgr] 启动文件定时器: {id}, 将在 {duration_seconds} 秒后播放下一首")

    def _clear_timer(self, id: str, timer_dict: Dict[str, str], job_prefix: str):
        """清除定时器"""
        if id in timer_dict:
            scheduler = scheduler_mgr
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
        scheduler = scheduler_mgr
        job_id = f"playlist_duration_timer_{id}"
        p_name = self._playlist_raw.get(id, {}).get("name", "未知播放列表")

        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        def stop_playlist_task(pid=id):
            p_name = self._playlist_raw.get(pid, {}).get("name", "未知播放列表")
            log.info(f"[PlaylistMgr] 播放列表时长定时器触发: {pid} - {p_name}")
            self._clear_timer(pid, self._playlist_duration_timers, "playlist_duration_timer_")
            self._scheduled_play_start_times.pop(pid, None)
            self.stop(pid)

        # 使用 DateTrigger 在指定时间后执行
        run_date = datetime.datetime.now() + timedelta(minutes=duration_minutes)
        scheduler.add_date_job(func=stop_playlist_task, job_id=job_id, run_date=run_date)
        self._playlist_duration_timers[id] = job_id
        log.info(f"[PlaylistMgr] 启动播放列表时长定时器: {id} - {p_name}, 将在 {duration_minutes} 分钟后停止播放")


# 全局实例
playlist_mgr = PlaylistMgr()
