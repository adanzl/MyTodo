import datetime
import os
import sys
import time
from queue import Queue
from typing import Any, Dict, List, Optional, Tuple

from gevent import spawn, sleep

from core.config import app_logger
from core.utils import get_media_duration, get_weekday_index
from core.services.playlist.constants import _TS
from core.services.playlist.devices import PlaylistDevices
from core.services.playlist.duration_fetch import DurationFetcher
from core.services.playlist.format_convert import PlaylistFormatConvert
from core.services.playlist.repository import PlaylistRepository
from core.services.playlist.scheduling import PlaylistScheduling

log = app_logger


def _get_pre_list_for_today(pre_lists: List[List]) -> List:
    """取 pre_lists（7 元素，周一到周日）中今天对应的那一项；输入不合法返回 `[]`。"""
    if not pre_lists or len(pre_lists) != 7:
        return []
    idx = get_weekday_index()
    if not 0 <= idx < 7:
        return []
    item = pre_lists[idx]
    return item if isinstance(item, list) else []


class PlaylistMgr:
    """播放列表管理器。

    该服务负责：
    - 播放列表数据的 CRUD（通过 RDS 持久化）
    - 播放状态机与游标（pre_lists 按周 + playlist）
    - 与设备层交互（play/stop/get_status/set_volume）
    - 定时任务（cron 自动播放、文件结束自动切下一首、播放列表时长限制）

    并发模型说明：
    - 主流程运行在 gevent 环境；
    - 批量获取媒体时长使用线程执行；
    - 线程侧不直接操作 Redis，而是通过 `_rds_save_queue` 将保存请求传递给 gevent worker。
    """

    def __init__(self) -> None:
        self._playing_playlists = set()  # 正在播放的播放列表ID集合
        self._playlist_raw = {}  # 播放列表数据
        self._devices = PlaylistDevices()
        self._play_state = {}  # 播放状态跟踪 {playlist_id: {'in_pre_files': bool, 'pre_index': int, 'file_index': int}}
        self._needs_reload = False  # 标记是否需要重新从 RDS 加载
        self._rds_save_queue = Queue()  # Redis 保存操作队列（用于从线程传递到 gevent 环境）
        self._last_play_sent_at = {}  # 向设备发送 play 的时间 {playlist_id: datetime}，用于停止时判断是否需延迟再发 stop
        # P1: RDS 读写迁出到 PlaylistRepository。用 provider 避免 _playlist_raw 重赋值导致引用过期。
        self._repo = PlaylistRepository(
            playlist_raw_provider=lambda: self._playlist_raw,
            rds_save_queue=self._rds_save_queue,
        )
        # P2: 批量获取媒体时长（ffprobe 子进程）迁出到 DurationFetcher。
        self._duration_fetcher = DurationFetcher(
            playlist_raw_provider=lambda: self._playlist_raw,
            rds_save_queue=self._rds_save_queue,
            save_async=lambda: spawn(self._repo.save, swallow_errors=True),
        )
        self._format_convert = PlaylistFormatConvert(
            playlist_raw_provider=lambda: self._playlist_raw,
            rds_save_queue=self._rds_save_queue,
        )
        # P3: 调度（cron / 定时器 / guard / reload 恢复）迁出到 PlaylistScheduling。
        self._scheduling = PlaylistScheduling(
            playlist_raw_provider=lambda: self._playlist_raw,
            devices_provider=lambda: self._devices,
            playing_playlists_provider=lambda: self._playing_playlists,
            save_async=lambda: spawn(self._repo.save, swallow_errors=True),
            on_play=self.play,
            on_stop=self.stop,
            on_file_timer_fire=self._on_file_timer_fire,
        )
        self.reload()
        self._repo.start_save_worker()  # 启动 Redis 保存操作的 worker
        self._scheduling.ensure_duration_guard_job()  # 启动播放列表时长守护任务

    def get_playlist(self, id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """获取播放列表。

        Args:
            id: 播放列表ID，如果为 None 则返回所有播放列表。

        Returns:
            播放列表字典，格式为 {playlist_id: playlist_data}。如果 id 为 None，
            返回所有播放列表；如果 id 有值，返回只包含该播放列表的字典；如果不存在则返回空字典。
            如果播放列表中有 isPlaying 字段，表示正在播放；如果正在播放当天前置列表，
            会添加 pre_index 字段表示当前播放的 pre_file 索引。
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
        self._duration_fetcher.start_batch_fetch(result)

        return result

    def get_playlist_history(self, limit: int = 10) -> Dict[str, str]:
        """获取播放列表历史记录（从 Redis Hash）。

        Args:
            limit: 返回的历史记录数量，默认10个。

        Returns:
            历史记录字典，格式为 {timestamp: json_str}，按时间倒序排列。
        """
        return self._repo.get_history(limit)

    def save_playlist(self, collection: Dict[str, Any]) -> int:
        """保存整个播放列表集合并持久化到 RDS。

        Args:
            collection: 播放列表集合字典，格式为 {playlist_id: playlist_data}。

        Returns:
            0 表示成功。
        """
        # 检查是否有任何播放列表正在转换
        for playlist_id in collection.keys():
            if self._format_convert.is_converting(playlist_id):
                log.warning(f"[PlaylistMgr] 播放列表 {playlist_id} 正在转换中，禁止修改")
                return -1

        self._playlist_raw = collection
        self._repo.save()
        # 更新设备映射
        self._refresh_device_map()
        return 0

    def update_single_playlist(self, playlist_data: Dict[str, Any]) -> int:
        """更新或创建单个播放列表。

        如果 playlist_id 已存在，则合并更新；否则创建新列表。
        此操作会同步更新 RDS、设备映射和 cron 定时任务。

        Args:
            playlist_data: 播放列表数据，必须包含 "id" 字段。

        Returns:
            0 表示成功，-1 表示失败。
        """
        try:
            if not playlist_data or not isinstance(playlist_data, dict):
                return -1

            playlist_id = playlist_data.get("id")
            if not playlist_id:
                log.error("[PlaylistMgr] update_single_playlist: playlist_data 中缺少 id 字段")
                return -1

            # 检查播放列表是否正在转换
            if self._format_convert.is_converting(playlist_id):
                log.warning(f"[PlaylistMgr] 播放列表 {playlist_id} 正在转换中，禁止修改")
                return -1

            # 如果播放列表不存在，创建新播放列表
            if playlist_id not in self._playlist_raw:
                log.info(f"[PlaylistMgr] 创建新播放列表: {playlist_id}")

            # 更新播放列表数据（合并现有数据，保留原有字段）
            if playlist_id in self._playlist_raw:
                self._playlist_raw[playlist_id].update(playlist_data)
            else:
                self._playlist_raw[playlist_id] = playlist_data

            # 保存到 RDS 和更新设备映射
            self._repo.save()
            self._devices.refresh_single(playlist_id, self._playlist_raw[playlist_id])
            self._scheduling.refresh_cron_job(playlist_id, self._playlist_raw[playlist_id])

            return 0
        except Exception as e:
            pid = playlist_data.get("id", "?") if isinstance(playlist_data, dict) else "?"
            log.error(f"[PlaylistMgr] update_single_playlist error: id={pid}, {e}", exc_info=True)
            return -1

    def reload(self) -> int:
        """从 RDS 重新加载所有播放列表数据。

        此操作会清空并重建内存中的播放列表、设备映射和定时任务。
        在非 Linux 平台，此操作会被跳过。

        Returns:
            0 表示成功，-1 表示失败。
        """
        if sys.platform != "linux":
            log.warning(f"[PlaylistMgr] Reload not supported on non-linux platforms : {sys.platform}")
            self._needs_reload = False
            return 0
        try:
            raw = self._repo.load_raw()
            if raw is not None:
                self._playlist_raw = raw

            # 保留 isPlaying / 定时器固化字段，便于进程重启后由 PlaylistScheduling.restore_timers_from_persistence 恢复 APScheduler 任务。
            # 当前 RDS 存档均为合法 pre_lists（7 个 list）；仅对损坏/旧字段做格式修复，不再读取已废弃的顶层 pre_files。
            migrated = False
            for playlist_id, playlist_data in self._playlist_raw.items():
                pre_lists = playlist_data.get("pre_lists", [])
                if not isinstance(pre_lists, list) or len(pre_lists) != 7:
                    playlist_data["pre_lists"] = [[] for _ in range(7)]
                    log.info(f"[PlaylistMgr] 修复 pre_lists 为 7 日结构: {playlist_id}")
                    migrated = True

            # 从 _playlist_raw 恢复游标状态到 _play_state，保留游标以便从上次位置继续
            # 只恢复那些在 _play_state 中不存在的播放列表（程序启动时的情况）
            # 如果 _play_state 中已有状态，则保留它（程序运行中的情况）
            for playlist_id, playlist_data in self._playlist_raw.items():
                if playlist_id not in self._play_state:
                    # 如果 _play_state 中没有该播放列表的状态，从 _playlist_raw 恢复游标
                    current_index = playlist_data.get("current_index", 0)
                    pre_lists = playlist_data.get("pre_lists", [])
                    pre_files = _get_pre_list_for_today(pre_lists)  # 获取今天对应的前置文件列表
                    if playlist_data.get("isPlaying"):
                        # 仅当 RDS 里成对存在 play_in_pre_files + play_pre_index 时才按持久化游标恢复；
                        # 单独存在任一字段（如历史脏数据）则走下面 elif/else 启发式，避免误恢复。
                        if "play_in_pre_files" in playlist_data and "play_pre_index" in playlist_data:
                            self._play_state[playlist_id] = {
                                "in_pre_files": bool(playlist_data.get("play_in_pre_files")),
                                "pre_index": int(playlist_data.get("play_pre_index", 0)),
                                "file_index": current_index,
                            }
                        elif pre_files:
                            self._play_state[playlist_id] = {
                                "in_pre_files": True,
                                "pre_index": 0,
                                "file_index": current_index
                            }
                        else:
                            self._play_state[playlist_id] = {
                                "in_pre_files": False,
                                "pre_index": 0,
                                "file_index": current_index
                            }
                    elif pre_files:
                        # 当天 pre_list 非空，从当日前置曲开始
                        self._play_state[playlist_id] = {
                            "in_pre_files": True,
                            "pre_index": 0,
                            "file_index": current_index
                        }
                    else:
                        # 当天无前置曲，从 playlist 的 current_index 开始
                        self._play_state[playlist_id] = {
                            "in_pre_files": False,
                            "pre_index": 0,
                            "file_index": current_index
                        }

            # 清除那些已不在 _playlist_raw 中的播放列表的状态
            playlist_ids_to_remove = [pid for pid in self._play_state.keys() if pid not in self._playlist_raw]
            for pid in playlist_ids_to_remove:
                self._play_state.pop(pid, None)

            # 清除内存运行时状态；正在播的列表由 scheduling.restore_timers_from_persistence 根据 RDS 字段恢复
            self._playing_playlists.clear()
            self._scheduling.scheduled_play_start_times.clear()

            if migrated:
                try:
                    self._repo.save()
                except Exception as e:
                    log.warning(f"[PlaylistMgr] reload 修复 pre_lists 后保存失败: {e}")

            self._refresh_device_map()
            self._scheduling.restore_timers_from_persistence()
            self._needs_reload = False
            log.info(f"[PlaylistMgr] Load success: {len(self._playlist_raw)} playlists")
            return 0
        except Exception as e:
            log.error(f"[PlaylistMgr] Reload error: {e}")
            self._needs_reload = True
            return -1

    def _refresh_device_map(self) -> None:
        """刷新所有播放列表的设备映射。"""
        self._devices.refresh_all(
            self._playlist_raw or {},
            on_each_playlist=lambda pid, data: self._scheduling.refresh_cron_job(pid, data),
        )
        self._cleanup_orphans()

    def _cleanup_orphans(self) -> None:
        """清理孤儿：APScheduler 上的所有 prefix 任务 + scheduling 自有 dict + mgr 自有 dict（_play_state / _last_play_sent_at / _playing_playlists）。"""
        valid_ids = set(self._playlist_raw.keys() if self._playlist_raw else [])
        self._scheduling.cleanup_orphaned_jobs(valid_ids)
        for state_dict in (self._play_state, self._last_play_sent_at):
            for pid in list(state_dict.keys()):
                if pid not in valid_ids:
                    del state_dict[pid]
        self._playing_playlists &= valid_ids

    def _validate_playlist(self, id: str) -> Tuple[Dict[str, Any], int, str | None]:
        """验证播放列表是否存在且有效。"""
        if not self._playlist_raw or id not in self._playlist_raw:
            return {}, -1, "播放列表不存在"
        playlist_data = self._playlist_raw[id]
        pre_lists = playlist_data.get("pre_lists", [])
        pre_files = _get_pre_list_for_today(pre_lists)  # 获取今天对应的前置文件列表
        playlist = playlist_data.get("playlist", [])
        if not playlist and not pre_files:
            return {}, -1, "播放列表为空"
        if self._devices.get(id) is None:
            return {}, -1, "设备不存在或未初始化"
        return playlist_data, 0, None

    def _init_play_state(self, id: str, playlist_data: Dict[str, Any], pre_files: List) -> None:
        """初始化播放状态。

        Args:
            id: 播放列表ID。
            playlist_data: 播放列表数据。
            pre_files: 前置文件列表。
        """
        current_index = playlist_data.get("current_index", 0)
        self._play_state[id] = {"in_pre_files": bool(pre_files), "pre_index": 0, "file_index": current_index}

    def _get_pre_files_for_today(self, playlist_data: Dict[str, Any]) -> List:
        """获取今天对应的前置文件列表。"""
        pre_lists = playlist_data.get("pre_lists", [])
        return _get_pre_list_for_today(pre_lists)

    def _get_current_file(self, play_state: Dict[str, Any], pre_files: List, playlist: List) -> tuple[Any, str | None]:
        """获取当前要播放的文件。"""
        if play_state["in_pre_files"]:
            pre_index = play_state["pre_index"]
            if pre_index < 0 or pre_index >= len(pre_files):
                return None, f"pre_files 索引 {pre_index} 超出范围"
            return pre_files[pre_index], None
        else:
            file_index = play_state["file_index"]
            if file_index < 0 or file_index >= len(playlist):
                return None, f"playlist 索引 {file_index} 超出范围"
            return playlist[file_index], None

    def _cleanup_play_state(self, id: str) -> None:
        """清理播放状态。"""
        self._scheduling.clear_all_for(id)
        self._playing_playlists.discard(id)
        self._play_state.pop(id, None)
        playlist_data = self._playlist_raw.get(id)
        if playlist_data:
            need_save = False
            for key in ("isPlaying", "play_in_pre_files", "play_pre_index", "duration_timer_at", "file_timer_at"):
                if key in playlist_data:
                    del playlist_data[key]
                    need_save = True
            if need_save:
                spawn(self._repo.save, swallow_errors=True)

    def play(self, id: str, force: bool = False) -> tuple[int, str]:
        """开始播放指定播放列表。

        播放逻辑：
        1) 先播放当天的 pre_files（来自 pre_lists）；
        2) 再从 playlist[current_index] 开始播放。

        该方法会与设备层交互（set_volume/play），并根据文件时长启动文件定时器；
        若配置了播放列表时长限制，也会启动时长定时器。

        Args:
            id: 播放列表 ID。
            force: 是否强制播放。若为 False 且当前列表已在播放中则返回失败。

        Returns:
            (code, msg)。code=0 表示成功开始播放。
        """
        if not force and id in self._playing_playlists:
            return -1, "播放列表正在播放中，请勿重复播放"

        playlist_data, code, msg = self._validate_playlist(id)
        if code != 0:
            return code, msg or "验证失败"

        pre_files = self._get_pre_files_for_today(playlist_data)  # 获取今天对应的前置文件列表
        playlist = playlist_data.get("playlist", [])

        # 初始化播放状态（如果不是 force 模式或状态不存在）
        if not force or id not in self._play_state:
            self._init_play_state(id, playlist_data, pre_files)

        play_state = self._play_state[id]
        file_item, error_msg = self._get_current_file(play_state, pre_files, playlist)
        if error_msg:
            return -1, error_msg

        file_path = file_item.get("uri")
        if not file_path:
            return -1, "文件路径无效"

        log.info(f"[PlaylistMgr] play: id={id}, force={force}, file={file_path}")

        # 获取并更新文件时长
        file_duration_seconds = self._duration_fetcher.update_file_duration(file_path, file_item)

        device = self._devices.get_obj(id)
        if device is None:
            # 正常路径下 _validate_playlist 已保证设备存在；这里防御 validate→get 之间的极端竞态。
            return -1, "设备不存在或未初始化"
        self._devices.apply_volume(id, device, playlist_data)

        code, msg = device.play(file_path)

        if code != 0:
            log.warning(f"[PlaylistMgr] play failed: id={id}, code={code}, msg={msg}")
            return code, msg

        # 记录向设备发送 play 的时间，供停止时判断是否需延迟再发 stop（设备加载中可能忽略第一次 stop）
        self._last_play_sent_at[id] = datetime.datetime.now()

        # 标记为正在播放
        self._playing_playlists.add(id)
        playlist_data['isPlaying'] = True
        playlist_data["play_in_pre_files"] = bool(play_state["in_pre_files"])
        playlist_data["play_pre_index"] = int(play_state["pre_index"])
        spawn(self._repo.save, swallow_errors=True)
        self._scheduling.clear_file_timer(id)

        # 启动文件定时器
        if file_duration_seconds and file_duration_seconds > 0:
            # 这个地方少1s，避免设备播放完成后自动重播导致重复播放
            self._scheduling.start_file_timer(id, max(file_duration_seconds - 1, 3))

        # 启动播放列表时长限制定时器（内部 idempotent，自管理 _scheduled_play_start_times）
        playlist_duration_minutes = playlist_data.get("schedule", {}).get("duration", 0)
        if playlist_duration_minutes > 0:
            self._scheduling.start_playlist_duration_timer(id, playlist_duration_minutes)

        return 0, "播放成功"

    def play_file_on_device(self, playlist_id: str, file_uri: str) -> tuple[int, str]:
        """在指定播放列表绑定的设备上播放指定文件（单次推播，不改变列表播放状态）。

        Args:
            playlist_id: 播放列表 ID。
            file_uri: 文件路径或 URI。

        Returns:
            (code, msg)。code=0 表示成功。
        """
        if not file_uri or not str(file_uri).strip():
            return -1, "文件地址无效"
        if not self._playlist_raw or playlist_id not in self._playlist_raw:
            return -1, "播放列表不存在"
        device = self._devices.get_obj(playlist_id)
        if device is None:
            return -1, "该播放列表未绑定设备，请先在配置中设置设备"
        playlist_data = self._playlist_raw[playlist_id]
        self._devices.apply_volume(playlist_id, device, playlist_data)

        code, msg = device.play(file_uri.strip())
        if code != 0:
            log.warning(f"[PlaylistMgr] play_file_on_device failed: id={playlist_id}, code={code}, msg={msg}")
            return code, msg
        self._last_play_sent_at[playlist_id] = datetime.datetime.now()

        # 启动文件定时器，到时间后停止设备
        self._scheduling.clear_file_on_device_timer(playlist_id)
        file_duration_seconds = get_media_duration(file_uri.strip())
        if file_duration_seconds and file_duration_seconds > 0:
            self._scheduling.start_file_on_device_timer(playlist_id, max(int(file_duration_seconds) - 1, 3))

        log.info(f"[PlaylistMgr] play_file_on_device ok: id={playlist_id}, uri={file_uri[:80]}")
        return 0, "已在设备上开始播放"

    def _update_index_and_play(self, id: str, in_pre_files: bool, pre_index: int, file_index: int) -> tuple[int, str]:
        """更新播放状态（游标），然后强制播放当前项。

        这是切歌（上一首/下一首/定时器触发）的核心逻辑，通过更新内部状态机
        的 in_pre_files, pre_index, file_index 来改变播放位置，然后
        调用 play(force=True) 来执行播放。

        Args:
            id: 播放列表 ID。
            in_pre_files: 是否正在播放前置文件。
            pre_index: 前置文件列表的当前索引。
            file_index: 主文件列表的当前索引。

        Returns:
            play() 方法的返回值。
        """
        try:
            playlist_data, code, msg = self._validate_playlist(id)
            if code != 0:
                return code, msg or "验证失败"

            pre_files = self._get_pre_files_for_today(playlist_data)  # 获取今天对应的前置文件列表
            playlist = playlist_data.get("playlist", [])

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

            # 更新播放列表的 current_index（只对 playlist 生效）
            if not play_state["in_pre_files"] and playlist:
                playlist_data["current_index"] = play_state["file_index"]
                playlist_data["updated_time"] = _TS()
                spawn(self._repo.save, swallow_errors=True)

            return self.play(id, force=True)
        except Exception as e:
            log.error(f"[PlaylistMgr] _update_index_and_play error: id={id}, {e}", exc_info=True)
            raise

    def play_next(self, id: str) -> tuple[int, str]:
        """播放下一首。

        根据当前播放状态（in_pre_files 或 playlist），自动递增游标并播放下一个文件。
        playlist 列表采用循环播放策略。

        Args:
            id: 播放列表 ID。

        Returns:
            (code, msg)。code=0 表示成功。

        Raises:
            Exception: 底层播放或状态更新异常。
        """
        try:
            playlist_data, code, msg = self._validate_playlist(id)
            if code != 0:
                return code, msg or "验证失败"

            pre_files = self._get_pre_files_for_today(playlist_data)  # 获取今天对应的前置文件列表
            playlist = playlist_data.get("playlist", [])

            # 如果没有播放状态，初始化并从头开始
            if id not in self._play_state:
                if pre_files:
                    return self._update_index_and_play(id,
                                                       in_pre_files=True,
                                                       pre_index=0,
                                                       file_index=playlist_data.get("current_index", 0))
                return self._update_index_and_play(id,
                                                   in_pre_files=False,
                                                   pre_index=0,
                                                   file_index=playlist_data.get("current_index", 0))

            play_state = self._play_state[id]

            if play_state["in_pre_files"]:
                # 播放 pre_files 的下一首
                next_pre_index = play_state["pre_index"] + 1
                if next_pre_index < len(pre_files):
                    return self._update_index_and_play(id,
                                                       in_pre_files=True,
                                                       pre_index=next_pre_index,
                                                       file_index=play_state["file_index"])
                # pre_files 播放完了，开始播放 playlist（从保存的 file_index 开始）
                if playlist and play_state["file_index"] < len(playlist):
                    return self._update_index_and_play(id,
                                                       in_pre_files=False,
                                                       pre_index=0,
                                                       file_index=play_state["file_index"])
                return -1, "没有更多文件可播放"
            else:
                # 播放 playlist 的下一首（使用取余实现循环）
                if playlist:
                    next_file_index = (play_state["file_index"] + 1) % len(playlist)
                    return self._update_index_and_play(id, in_pre_files=False, pre_index=0, file_index=next_file_index)
                return -1, "没有更多文件可播放"
        except Exception as e:
            log.error(f"[PlaylistMgr] play_next error: id={id}, {e}", exc_info=True)
            raise

    def play_pre(self, id: str) -> tuple[int, str]:
        """播放上一首。

        根据当前播放状态（in_pre_files 或 playlist），自动递减游标并播放上一个文件。
        当 playlist 在开头时，会回退到 pre_files 的最后一项（若存在）。

        Args:
            id: 播放列表 ID。

        Returns:
            (code, msg)。code=0 表示成功。
        """
        playlist_data, code, msg = self._validate_playlist(id)
        if code != 0:
            return code, msg or "验证失败"

        pre_files = self._get_pre_files_for_today(playlist_data)  # 获取今天对应的前置文件列表
        playlist = playlist_data.get("playlist", [])

        # 如果没有播放状态，初始化
        if id not in self._play_state:
            if pre_files:
                return self._update_index_and_play(id,
                                                   in_pre_files=True,
                                                   pre_index=len(pre_files) - 1,
                                                   file_index=playlist_data.get("current_index", 0))
            current_index = playlist_data.get("current_index", 0)
            prev_index = (current_index - 1) % len(playlist) if playlist else 0
            return self._update_index_and_play(id, in_pre_files=False, pre_index=0, file_index=prev_index)

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
            # 播放 playlist 的上一首
            prev_file_index = play_state["file_index"] - 1
            if prev_file_index >= 0:
                return self._update_index_and_play(id, in_pre_files=False, pre_index=0, file_index=prev_file_index)
            # playlist 在开头，回到 pre_files 的最后
            if pre_files:
                return self._update_index_and_play(id, in_pre_files=True, pre_index=len(pre_files) - 1, file_index=0)
            return -1, "已经是第一首"

    def stop(self, id: str) -> tuple[int, str]:
        """停止指定播放列表的播放。

        该方法会清理与该播放列表相关的运行时状态（播放状态、定时器等），并调用
        设备层的 stop() 停止实际播放。不要求播放列表非空，以便在仅做过「在设备上播放」
        单次推播时也能停止设备。

        Args:
            id: 播放列表 ID。

        Returns:
            (code, msg)。code=0 表示成功。
        """
        p_name = self._playlist_raw.get(id, {}).get("name", "未知播放列表")
        log.info(f"[PlaylistMgr] 停止播放: {id} - {p_name}")

        if not self._playlist_raw or id not in self._playlist_raw:
            return -1, "播放列表不存在"
        device = self._devices.get_obj(id)
        if device is None:
            log.warning(f"[PlaylistMgr] 停止播放失败 - 设备不存在: {id} - {p_name}")
            return -1, "设备不存在或未初始化"

        self._cleanup_play_state(id)

        code, msg = device.stop()
        if code == 0:
            log.info(f"[PlaylistMgr] 停止播放成功: {id} - {p_name}")
        else:
            log.error(f"[PlaylistMgr] 停止播放失败 - 设备停止失败: {id} - {p_name}, {msg}")

        # 若 3s 内向设备发过 play（如刚切歌），设备可能在加载中忽略了 stop，3s 后若列表仍为停止状态则再发一次 stop
        last_play_sent = self._last_play_sent_at.get(id)
        if last_play_sent and (datetime.datetime.now() - last_play_sent).total_seconds() < 3:
            verify_job_id = f"playlist_stop_verify_{id}"

            def _stop_verify_task(pid=id) -> None:
                if pid in self._playing_playlists or pid not in self._devices:
                    return
                c, m = self._devices.safe_stop(pid)
                p_name_verify = self._playlist_raw.get(pid, {}).get("name", "未知播放列表")
                log.info(
                    f"[PlaylistMgr] 停止验证: 列表已停止且 3s 内曾发过 play，再次向设备发 stop: "
                    f"{pid} - {p_name_verify}, code={c}, msg={m}"
                )

            self._scheduling.schedule_one_shot(verify_job_id, 3, _stop_verify_task)
            log.info(f"[PlaylistMgr] 3s 内曾向设备发过 play，已安排 3s 后验证并必要时再发 stop: {id} - {p_name}")

        return code, msg

    def trigger_button(self, button: str, action: str) -> tuple[int, str]:
        """响应外部按钮事件（如 Agent 上报）来播放或停止播放列表。

        - "stop": 停止所有绑定到该按钮的、且正在播放的播放列表。
        - "play": 播放第一个绑定到该按钮的、且其 cron 表达式在今天会触发的播放列表。

        Args:
            button: 按钮编号（例如 "B1", "B2"）。
            action: 操作类型 ("play" 或 "stop")。

        Returns:
            (code, msg)。code=0 表示成功。
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
            # play 操作：手动触发，选择第一个绑定该按钮的播放列表即可（不受 cron 是否今天触发限制）
            matching_playlists = []
            for playlist_id, playlist_data in self._playlist_raw.items():
                if playlist_data.get("trigger_button") == button:
                    matching_playlists.append((playlist_id, playlist_data))

            if not matching_playlists:
                return -1, f"未找到触发按钮 {button} 对应的播放列表"

            target_playlist_id = matching_playlists[0][0]
            return self.play(target_playlist_id)

        else:
            return -1, f"不支持的操作: {action}"

    def _on_file_timer_fire(self, pid: str) -> None:
        """文件播放结束定时器触发：根据设备进度微调后切下一首。"""
        state, remaining = self._devices.read_progress(pid)
        # 设备已停 → 直接切；仍在播 → 让它把当前文件放完再切，上限 5s 防卡死。
        if state != "STOPPED" and remaining >= 2:
            time.sleep(min(remaining, 5))

        self._scheduling.clear_file_timer(pid)

        if pid not in self._play_state:
            log.warning(f"[PlaylistMgr] 文件定时器触发时播放状态丢失: {pid}，重新初始化")
            playlist_data = self._playlist_raw.get(pid)
            if not playlist_data:
                log.error(f"[PlaylistMgr] 文件定时器触发时播放列表数据不存在: {pid}")
                return
            pre_files = self._get_pre_files_for_today(playlist_data)
            self._init_play_state(pid, playlist_data, pre_files)

        stop_code, stop_msg = self._devices.safe_stop(pid)
        if stop_code != 0:
            log.warning(f"[PlaylistMgr] 停止当前播放失败: {pid}, {stop_msg}")

        try:
            code, msg = self.play_next(pid)
            if code != 0:
                log.warning(f"[PlaylistMgr] 定时器触发播放下一首失败: {pid}, {msg}")
                self._cleanup_play_state(pid)
        except Exception as e:
            log.error(f"[PlaylistMgr] 定时器触发播放下一首异常: {pid}, {e}", exc_info=True)
            self._cleanup_play_state(pid)

    def convert_playlist_to_mp3(self, playlist_id: str) -> tuple[int, str]:
        """将播放列表中的所有文件转换为MP3格式，删除原始文件并替换为新文件。

        Args:
            playlist_id: 播放列表ID。

        Returns:
            (code, msg)。code=0 表示成功开始转换任务。
        """
        return self._format_convert.convert_playlist_to_mp3(playlist_id)

    def playlist_verify(self, playlist_id: str) -> tuple[int, str]:
        """校验列表文件是否存在，移除不存在的项。"""
        try:
            if not self._playlist_raw or playlist_id not in self._playlist_raw:
                return -1, "播放列表不存在"

            data = self._playlist_raw[playlist_id]
            p_name = data.get("name", "未知播放列表")
            removed = 0
            file_lists: List[List] = []
            pre_lists = data.get("pre_lists", [])
            if isinstance(pre_lists, list) and len(pre_lists) == 7:
                file_lists.extend(pl for pl in pre_lists if isinstance(pl, list))
            playlist = data.get("playlist", [])
            if isinstance(playlist, list):
                file_lists.append(playlist)

            for lst in file_lists:
                kept = [
                    x for x in lst
                    if isinstance(x, dict) and (u := x.get("uri")) and os.path.exists(str(u).strip())
                ]
                removed += len(lst) - len(kept)
                lst[:] = kept

            n = len(playlist) if isinstance(playlist, list) else 0
            data["current_index"] = min(data.get("current_index", 0), max(0, n - 1)) if n else 0
            if playlist_id in self._play_state:
                ps = self._play_state[playlist_id]
                pre_n = len(self._get_pre_files_for_today(data))
                ps["pre_index"] = min(ps.get("pre_index", 0), max(0, pre_n - 1)) if pre_n else 0
                ps["file_index"] = min(ps.get("file_index", 0), max(0, n - 1)) if n else 0

            if removed == 0:
                return 0, f"播放列表 {p_name} 中所有文件均存在"

            data["updated_time"] = _TS()
            spawn(self._repo.save, swallow_errors=True)
            log.info(f"[PlaylistMgr] 播放列表 {playlist_id} 已移除 {removed} 个不存在文件")
            return 0, f"已从播放列表 {p_name} 中移除 {removed} 个不存在文件"
        except Exception as e:
            log.error(f"[PlaylistMgr] playlist_verify 异常: {playlist_id}, {e}", exc_info=True)
            return -1, f"校验失败: {str(e)}"

    def playlist_remove_duplicate(self, playlist_id: str) -> tuple[int, str]:
        """移除播放列表中的重复文件路径。

        Args:
            playlist_id: 播放列表ID。

        Returns:
            (code, msg)。code=0 表示成功。
        """
        try:
            if not self._playlist_raw or playlist_id not in self._playlist_raw:
                return -1, "播放列表不存在"

            playlist_data = self._playlist_raw[playlist_id]
            p_name = playlist_data.get("name", "未知播放列表")

            # 执行去重
            removed_count = 0
            seen_uris = set()

            # 处理pre_lists
            pre_lists = playlist_data.get("pre_lists", [])
            if isinstance(pre_lists, list) and len(pre_lists) == 7:
                for pre_list in pre_lists:
                    if isinstance(pre_list, list):
                        new_pre_list = []
                        for item in pre_list:
                            uri = item.get("uri")
                            if uri and uri not in seen_uris:
                                seen_uris.add(uri)
                                new_pre_list.append(item)
                            elif uri:
                                removed_count += 1
                        pre_list.clear()
                        pre_list.extend(new_pre_list)

            # 处理playlist
            playlist = playlist_data.get("playlist", [])
            new_playlist = []
            for item in playlist:
                uri = item.get("uri")
                if uri and uri not in seen_uris:
                    seen_uris.add(uri)
                    new_playlist.append(item)
                elif uri:
                    removed_count += 1

            playlist.clear()
            playlist.extend(new_playlist)

            if removed_count == 0:
                return 0, f"播放列表 {p_name} 中没有重复文件"

            spawn(self._repo.save, swallow_errors=True)

            log.info(f"[PlaylistMgr] 播放列表 {playlist_id} 已移除 {removed_count} 个重复文件")
            return 0, f"已从播放列表 {p_name} 中移除 {removed_count} 个重复文件"

        except Exception as e:
            log.error(f"[PlaylistMgr] playlist_remove_duplicate 异常: {playlist_id}, {e}", exc_info=True)
            return -1, f"去重失败: {str(e)}"

    def set_current_index(self, playlist_id: str, index: int, in_pre_files: bool = False) -> tuple[int, str]:
        """设置播放列表的当前播放位置（游标）。

        Args:
            playlist_id: 播放列表ID。
            index: 要设置的索引位置。
            in_pre_files: 是否在前置文件中设置游标。

        Returns:
            (code, msg)。code=0 表示成功。
        """
        try:
            playlist_data, code, msg = self._validate_playlist(playlist_id)
            if code != 0:
                return code, msg or "验证失败"

            pre_files = self._get_pre_files_for_today(playlist_data)
            playlist = playlist_data.get("playlist", [])

            # 验证索引范围
            if in_pre_files:
                if not pre_files or index < 0 or index >= len(pre_files):
                    return -1, f"前置文件索引 {index} 超出范围 (0-{len(pre_files)-1 if pre_files else -1})"
            else:
                if not playlist or index < 0 or index >= len(playlist):
                    return -1, f"播放列表索引 {index} 超出范围 (0-{len(playlist)-1 if playlist else -1})"

            # 初始化播放状态（如果不存在）
            if playlist_id not in self._play_state:
                self._init_play_state(playlist_id, playlist_data, pre_files)

            play_state = self._play_state[playlist_id]

            # 更新播放状态
            play_state["in_pre_files"] = in_pre_files
            if in_pre_files:
                play_state["pre_index"] = index
            else:
                play_state["file_index"] = index

            # 更新播放列表的 current_index（只对 playlist 生效）
            if not in_pre_files and playlist:
                playlist_data["current_index"] = index
                playlist_data["updated_time"] = _TS()
                spawn(self._repo.save, swallow_errors=True)

            p_name = playlist_data.get("name", "未知播放列表")
            log.info(f"[PlaylistMgr] 设置播放列表 {playlist_id} 游标: in_pre_files={in_pre_files}, index={index}")
            return 0, f"已设置播放列表 {p_name} 的当前位置为第 {index + 1} 项"

        except Exception as e:
            log.error(f"[PlaylistMgr] set_current_index 异常: {playlist_id}, {e}", exc_info=True)
            return -1, f"设置游标失败: {str(e)}"


# 全局实例
playlist_mgr = PlaylistMgr()
