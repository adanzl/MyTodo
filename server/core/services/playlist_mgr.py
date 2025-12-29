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
from core.device import create_device
from core.log_config import root_logger
from core.services.scheduler_mgr import scheduler_mgr
from core.utils import time_to_seconds

log = root_logger()

PLAYLIST_RDS_FULL_KEY = "schedule_play:playlist_collection"
DEFAULT_PLAYLIST_NAME = "默认播放列表"
DEVICE_TYPES = {"device_agent", "bluetooth", "dlna", "mi"}

_TS = lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _get_weekday_index():
    """
    获取当前星期对应的索引
    返回: 0=周一, 1=周二, 2=周三, 3=周四, 4=周五, 5=周六, 6=周日
    """
    weekday = datetime.datetime.now().weekday()  # 0=周一, 6=周日
    return weekday


def _get_pre_list_for_today(pre_lists):
    """
    获取今天对应的前置文件列表
    :param pre_lists: pre_lists 数组，固定7个元素，分别代表周一到周日
    :return: 今天对应的前置文件列表
    """
    if not pre_lists or len(pre_lists) != 7:
        return []
    weekday_index = _get_weekday_index()
    return pre_lists[weekday_index] if isinstance(pre_lists[weekday_index], list) else []


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
                 如果正在播放 pre_files，会添加 pre_index 字段表示当前播放的 pre_file 索引
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

        # 为正在播放的列表添加播放状态信息
        for playlist_id, playlist_data in result.items():
            if playlist_id in self._play_state:
                play_state = self._play_state[playlist_id]
                # 添加 in_pre_files 状态，用于前端判断显示哪个列表的"播放中" tag
                playlist_data["in_pre_files"] = play_state.get("in_pre_files", False)
                if play_state.get("in_pre_files", False):
                    # 正在播放 pre_files，添加 pre_index
                    playlist_data["pre_index"] = play_state.get("pre_index", -1)
                else:
                    # 不在播放 pre_files，清除 pre_index（设置为 -1 表示无效）
                    playlist_data["pre_index"] = -1
            else:
                # 播放列表不在播放状态，设置默认值
                playlist_data["in_pre_files"] = False
                playlist_data["pre_index"] = -1

        # 汇总所有没有 duration 的文件，启动单例线程批量获取时长
        self._start_batch_duration_fetch(result)

        return result

    def _save_playlist_to_rds(self):
        """保存播放列表到 RDS"""
        try:
            json_str = json.dumps(self._playlist_raw, ensure_ascii=False)
            rds_mgr.set(PLAYLIST_RDS_FULL_KEY, json_str)
        except Exception as e:
            log.error(f"[PlaylistMgr] _save_playlist_to_rds error: {e}", exc_info=True)
            raise

    def save_playlist(self, collection: Dict[str, Any]) -> int:
        """
        保存整个播放列表集合
        :param collection: 播放列表集合字典，格式为 {playlist_id: playlist_data}
        """
        self._playlist_raw = collection
        self._save_playlist_to_rds()
        # 更新设备映射
        self._refresh_device_map()
        return 0

    def update_single_playlist(self, playlist_data: Dict[str, Any]) -> int:
        """
        更新单个播放列表
        :param playlist_data: 播放列表数据，必须包含 id 字段
        :return: 0 表示成功，-1 表示失败
        """
        try:
            if not playlist_data or not isinstance(playlist_data, dict):
                return -1

            playlist_id = playlist_data.get("id")
            if not playlist_id:
                log.error("[PlaylistMgr] update_single_playlist: playlist_data 中缺少 id 字段")
                return -1

            # 如果播放列表不存在，创建新播放列表
            if playlist_id not in self._playlist_raw:
                log.info(f"[PlaylistMgr] 创建新播放列表: {playlist_id}")

            # 更新播放列表数据（合并现有数据）
            if playlist_id in self._playlist_raw:
                # 合并更新，保留原有字段
                existing_playlist = self._playlist_raw[playlist_id]
                existing_playlist.update(playlist_data)
                self._playlist_raw[playlist_id] = existing_playlist
            else:
                # 新播放列表
                self._playlist_raw[playlist_id] = playlist_data

            # 保存到 RDS 和更新设备映射
            self._save_playlist_to_rds()
            self._refresh_single_device_map(playlist_id, self._playlist_raw[playlist_id])
            self._refresh_cron_job(playlist_id, self._playlist_raw[playlist_id])

            return 0
        except Exception as e:
            log.error(f"[PlaylistMgr] update_single_playlist error: id={playlist_id}, {e}", exc_info=True)
            return -1

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

            # 清除所有播放列表的 isPlaying 状态（程序重启后，播放状态不应该保留）
            for playlist_id, playlist_data in self._playlist_raw.items():
                if 'isPlaying' in playlist_data:
                    del playlist_data['isPlaying']

                # 迁移 pre_files 到 pre_lists（如果还没有 pre_lists）
                if "pre_lists" not in playlist_data:
                    pre_files = playlist_data.get("pre_files", [])
                    # 创建 pre_lists，固定7个元素，分别代表周一到周日
                    # 将 pre_files 复制到这7个列表中
                    pre_lists = [list(pre_files) for _ in range(7)]  # 深拷贝到7个列表
                    playlist_data["pre_lists"] = pre_lists
                    log.info(f"[PlaylistMgr] 迁移 pre_files 到 pre_lists: {playlist_id}, 共 {len(pre_files)} 个文件")
                elif not isinstance(playlist_data.get("pre_lists"), list) or len(playlist_data.get("pre_lists",
                                                                                                   [])) != 7:
                    # 如果 pre_lists 存在但格式不正确，重新初始化
                    pre_files = playlist_data.get("pre_files", [])
                    pre_lists = [list(pre_files) for _ in range(7)]
                    playlist_data["pre_lists"] = pre_lists
                    log.info(f"[PlaylistMgr] 修复 pre_lists 格式: {playlist_id}")

            # 从 _playlist_raw 恢复游标状态到 _play_state，保留游标以便从上次位置继续
            # 只恢复那些在 _play_state 中不存在的播放列表（程序启动时的情况）
            # 如果 _play_state 中已有状态，则保留它（程序运行中的情况）
            for playlist_id, playlist_data in self._playlist_raw.items():
                if playlist_id not in self._play_state:
                    # 如果 _play_state 中没有该播放列表的状态，从 _playlist_raw 恢复游标
                    current_index = playlist_data.get("current_index", 0)
                    pre_lists = playlist_data.get("pre_lists", [])
                    pre_files = _get_pre_list_for_today(pre_lists)  # 获取今天对应的前置文件列表
                    if pre_files:
                        # 如果有 pre_files，从 pre_files 开始（从头开始）
                        self._play_state[playlist_id] = {
                            "in_pre_files": True,
                            "pre_index": 0,
                            "file_index": current_index
                        }
                    else:
                        # 如果没有 pre_files，从 files 的 current_index 开始
                        self._play_state[playlist_id] = {
                            "in_pre_files": False,
                            "pre_index": 0,
                            "file_index": current_index
                        }

            # 清除那些已不在 _playlist_raw 中的播放列表的状态
            playlist_ids_to_remove = [pid for pid in self._play_state.keys() if pid not in self._playlist_raw]
            for pid in playlist_ids_to_remove:
                del self._play_state[pid]

            # 清除运行时状态（这些状态不应该在重启后保留）
            self._playing_playlists.clear()
            self._scheduled_play_start_times.clear()

            # 如果清除了 isPlaying 状态，保存回 RDS
            if self._playlist_raw:
                self._save_playlist_to_rds()

            self._refresh_device_map()
            self._needs_reload = False
            log.info(f"[PlaylistMgr] Load success: {len(self._playlist_raw)} playlists")
            return 0
        except Exception as e:
            log.error(f"[PlaylistMgr] Reload error: {e}")
            self._needs_reload = True
            return -1

    def _refresh_device_map(self):
        """刷新所有播放列表的设备映射"""
        self._device_map = {}
        if self._playlist_raw and sys.platform == "linux":
            for p_id in self._playlist_raw:
                playlist_data = self._playlist_raw[p_id]
                self._device_map[p_id] = create_device(playlist_data.get("device", {}))
                self._refresh_cron_job(p_id, playlist_data)
        self._cleanup_orphaned_cron_jobs()

    def _refresh_single_device_map(self, playlist_id: str, playlist_data: Dict[str, Any]):
        """只更新单个播放列表的设备映射"""
        try:
            if sys.platform != "linux":
                return
            device = playlist_data.get("device", {})
            if device and device.get("address"):
                device_type = device.get("type") or playlist_data.get("device_type", "dlna")
                if device_type in DEVICE_TYPES:
                    self._device_map[playlist_id] = create_device({
                        "type": device_type,
                        "address": device.get("address"),
                        "name": device.get("name")
                    })
                else:
                    # 如果设备类型无效，从映射中移除
                    log.warning(f"[PlaylistMgr] 设备类型无效: {playlist_id}, type={device_type}")
                    self._device_map.pop(playlist_id, None)
            else:
                # 如果没有设备地址，从映射中移除
                self._device_map.pop(playlist_id, None)
        except Exception as e:
            log.error(f"[PlaylistMgr] _refresh_single_device_map error: id={playlist_id}, {e}", exc_info=True)
            raise

    def _refresh_cron_job(self, playlist_id: str, playlist_data: Dict[str, Any]):
        try:
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
                    # 捕获 gevent 相关的异常，避免影响线程池 worker
                    import gevent
                    if isinstance(e, gevent.exceptions.LoopExit):
                        log.warning(f"[PlaylistMgr] 定时任务执行后发生 gevent LoopExit (可忽略): {pid} - {p_name}")
                    else:
                        log.error(f"[PlaylistMgr] 定时任务执行异常: {pid} - {p_name}, {e}")

            success = scheduler.add_cron_job(func=cron_play_task, job_id=job_id, cron_expression=cron_expression)
            playlist_name = playlist_data.get("name", "未知播放列表")
            if not success:
                log.error(f"[PlaylistMgr] 创建定时任务失败: {playlist_id}, {playlist_name}, cron: {cron_expression}")
        except Exception as e:
            log.error(f"[PlaylistMgr] _refresh_cron_job error: id={playlist_id}, {e}", exc_info=True)
            raise

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

        # 如果已经有 duration，直接返回，避免重复获取
        if file_item.get("duration"):
            return file_item.get("duration")

        duration = get_media_duration(file_path)
        if duration is None:
            return None

        file_duration_seconds = int(duration)
        # 更新时长（file_item 是列表中的引用，直接修改即可）
        file_item["duration"] = file_duration_seconds
        # RDS 保存改为异步，避免阻塞
        from gevent import spawn

        def save_async():
            try:
                self._save_playlist_to_rds()
            except Exception as e:
                log.warning(f"[PlaylistMgr] Async save duration error: {e}")

        spawn(save_async)
        return file_duration_seconds

    def _collect_files_without_duration(self, playlist_data: Dict[str, Any], check_blacklist: bool = True) -> set:
        """
        收集播放列表中没有 duration 的文件 URI
        :param playlist_data: 播放列表数据
        :param check_blacklist: 是否检查黑名单
        :return: 文件 URI 集合
        """
        files_to_fetch = set()

        # 检查 pre_lists（所有7天的列表）
        pre_lists = playlist_data.get("pre_lists", [])
        if isinstance(pre_lists, list) and len(pre_lists) == 7:
            for pre_list in pre_lists:
                if isinstance(pre_list, list):
                    for file_item in pre_list:
                        if not file_item.get("duration"):
                            file_uri = file_item.get("uri")
                            if file_uri:
                                if check_blacklist:
                                    failure_count = self._duration_blacklist.get(file_uri, 0)
                                    if failure_count < 3:
                                        files_to_fetch.add(file_uri)
                                else:
                                    files_to_fetch.add(file_uri)

        # 检查 files/playlist
        for file_item in playlist_data.get("files", []):
            if not file_item.get("duration"):
                file_uri = file_item.get("uri")
                if file_uri:
                    if check_blacklist:
                        failure_count = self._duration_blacklist.get(file_uri, 0)
                        if failure_count < 3:
                            files_to_fetch.add(file_uri)
                    else:
                        files_to_fetch.add(file_uri)

        return files_to_fetch

    def _update_files_duration(self, playlist_data: Dict[str, Any], file_durations: Dict[str, int]) -> int:
        """
        更新播放列表中匹配文件的 duration
        :param playlist_data: 播放列表数据
        :param file_durations: 文件 duration 字典 {file_uri: duration_seconds, ...}
        :return: 更新的文件数量
        """
        updated_count = 0

        # 更新 pre_lists（所有7天的列表）
        pre_lists = playlist_data.get("pre_lists", [])
        if isinstance(pre_lists, list) and len(pre_lists) == 7:
            for pre_list in pre_lists:
                if isinstance(pre_list, list):
                    for file_item in pre_list:
                        file_uri = file_item.get("uri")
                        if file_uri and file_uri in file_durations and not file_item.get("duration"):
                            file_item["duration"] = file_durations[file_uri]
                            updated_count += 1

        # 更新 pre_files（旧格式，兼容性处理）
        pre_files = playlist_data.get("pre_files", [])
        if isinstance(pre_files, list):
            for file_item in pre_files:
                file_uri = file_item.get("uri")
                if file_uri and file_uri in file_durations and not file_item.get("duration"):
                    file_item["duration"] = file_durations[file_uri]
                    updated_count += 1

        # 更新 files/playlist
        files = playlist_data.get("files", [])
        for file_item in files:
            file_uri = file_item.get("uri")
            if file_uri and file_uri in file_durations and not file_item.get("duration"):
                file_item["duration"] = file_durations[file_uri]
                updated_count += 1

        return updated_count

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
            files_to_fetch.update(self._collect_files_without_duration(playlist_data, check_blacklist=True))

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
                    updated_count += self._update_files_duration(playlist_data, file_durations)

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
        pre_lists = playlist_data.get("pre_lists", [])
        pre_files = _get_pre_list_for_today(pre_lists)  # 获取今天对应的前置文件列表
        files = playlist_data.get("files", [])
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

    def _get_pre_files_for_today(self, playlist_data: Dict[str, Any]) -> List:
        """获取今天对应的前置文件列表"""
        pre_lists = playlist_data.get("pre_lists", [])
        return _get_pre_list_for_today(pre_lists)

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

        pre_files = self._get_pre_files_for_today(playlist_data)  # 获取今天对应的前置文件列表
        files = playlist_data.get("files", [])

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

        file_path = file_item.get("uri")
        if not file_path:
            return -1, "文件路径无效"

        log.info(f"[PlaylistMgr] play: id={id}, force={force}, file={file_path}")

        # 获取并更新文件时长
        file_duration_seconds = self._update_file_duration(file_path, file_item)

        # 播放文件
        device = self._device_map[id]["obj"]
        code, msg = device.play(file_path)

        if code != 0:
            log.warning(f"[PlaylistMgr] play failed: id={id}, code={code}, msg={msg}")
            return code, msg

        # 标记为正在播放
        self._playing_playlists.add(id)
        playlist_data['isPlaying'] = True
        self._clear_timer(id, self._file_timers, "playlist_file_timer_")

        # 启动文件定时器
        if file_duration_seconds and file_duration_seconds > 0:
            # 这个地方少1s，避免设备播放完成后自动重播导致重复播放
            self._start_file_timer(id, max(file_duration_seconds - 1, 3))

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
        try:
            playlist_data, code, msg = self._validate_playlist(id)
            if code != 0:
                return code, msg

            pre_files = self._get_pre_files_for_today(playlist_data)  # 获取今天对应的前置文件列表
            files = playlist_data.get("files", [])

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
                # RDS 保存改为异步，避免阻塞播放操作
                from gevent import spawn

                def save_async():
                    try:
                        self._save_playlist_to_rds()
                    except Exception as e:
                        log.warning(f"[PlaylistMgr] Async save current_index error: {e}")

                spawn(save_async)

            return self.play(id, force=True)
        except Exception as e:
            log.error(f"[PlaylistMgr] _update_index_and_play error: id={id}, {e}", exc_info=True)
            raise

    def play_next(self, id: str) -> tuple[int, str]:
        """播放下一首"""
        try:
            playlist_data, code, msg = self._validate_playlist(id)
            if code != 0:
                return code, msg

            pre_files = self._get_pre_files_for_today(playlist_data)  # 获取今天对应的前置文件列表
            files = playlist_data.get("files", [])

            # 如果没有播放状态，初始化并从头开始
            if id not in self._play_state:
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
        except Exception as e:
            log.error(f"[PlaylistMgr] play_next error: id={id}, {e}", exc_info=True)
            raise

    def play_pre(self, id: str) -> tuple[int, str]:
        """播放上一首"""
        playlist_data, code, msg = self._validate_playlist(id)
        if code != 0:
            return code, msg

        pre_files = self._get_pre_files_for_today(playlist_data)  # 获取今天对应的前置文件列表
        files = playlist_data.get("files", [])

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
            device = self._device_map.get(pid, {}).get("obj")
            wait_seconds = 0
            if device:
                try:
                    code, status = device.get_status()
                    if code == 0:
                        device_state = status.get("state", "")
                        duration_str = status.get("duration", "00:00:00")
                        position_str = status.get("position", "00:00:00")
                        # 安全计算等待时间
                        try:
                            wait_seconds = time_to_seconds(duration_str) - time_to_seconds(position_str)
                        except (ValueError, AttributeError) as e:
                            log.warning(
                                f"[PlaylistMgr] 计算等待时间失败: {pid}, duration={duration_str}, position={position_str}, {e}")
                            wait_seconds = 0

                        # 如果设备状态是 STOPPED，说明文件已经播放完成，不需要等待
                        if device_state == "STOPPED":
                            try:
                                device.stop()
                            except Exception as e:
                                log.warning(f"[PlaylistMgr] 停止已停止的设备异常: {pid}, {e}")
                            wait_seconds = 0
                        elif wait_seconds >= 2:
                            # 如果还有剩余时间，等待一下（最多等待5秒，避免等待过久）
                            wait_seconds = min(wait_seconds, 5)
                            time.sleep(wait_seconds)
                    else:
                        # 获取状态失败，记录警告但继续执行切换下一首
                        log.warning(f"[PlaylistMgr] 获取设备状态失败: {pid}, {status.get('error', '未知错误')}")
                except Exception as e:
                    log.error(f"[PlaylistMgr] 检查播放状态异常: {pid}, {e}")

            # 清除定时器（避免重复触发）
            self._clear_timer(pid, self._file_timers, "playlist_file_timer_")

            # 确保播放状态存在，如果不存在则初始化
            if pid not in self._play_state:
                log.warning(f"[PlaylistMgr] 文件定时器触发时播放状态丢失: {pid}，重新初始化")
                playlist_data = self._playlist_raw.get(pid)
                if playlist_data:
                    pre_files = self._get_pre_files_for_today(playlist_data)  # 获取今天对应的前置文件列表
                    self._init_play_state(pid, playlist_data, pre_files)
                else:
                    log.error(f"[PlaylistMgr] 文件定时器触发时播放列表数据不存在: {pid}")
                    return

            # 在播放下一首之前，先停止当前播放，避免设备自动重播导致重复播放
            if device:
                try:
                    stop_code, stop_msg = device.stop()
                    if stop_code != 0:
                        log.warning(f"[PlaylistMgr] 停止当前播放失败: {pid}, {stop_msg}")
                except Exception as e:
                    log.warning(f"[PlaylistMgr] 停止当前播放异常: {pid}, {e}")

            # 播放下一首
            try:
                result = self.play_next(pid)
                # 如果播放失败，记录错误但不抛出异常（避免影响定时器）
                if result[0] != 0:
                    log.warning(f"[PlaylistMgr] 定时器触发播放下一首失败: {pid}, {result[1]}")
            except Exception as e:
                log.error(f"[PlaylistMgr] 定时器触发播放下一首异常: {pid}, {e}", exc_info=True)

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
