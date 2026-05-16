"""playlist 模块的调度子系统。

集中管理 APScheduler 上所有与播放列表相关的任务：

- cron 自动触发播放 + 孤儿清理
- 单文件结束后切下一首的 file_timer
- 单次推播文件到时停设备的 on-device timer
- 播放列表整体时长限制 timer
- 30s 一次的 duration guard
- 进程冷启动后从 RDS 固化字段恢复定时器
- 一次性任务（如 stop verify）

与 `PlaylistMgr` 编排层通过行为回调交互：`on_play` / `on_stop` /
`on_file_timer_fire`。禁止 `from core.services.playlist_mgr import playlist_mgr`。
"""

import datetime
import sys
from datetime import timedelta
from typing import Any, Callable, Dict, Set, Tuple

import gevent
from gevent import spawn

from core.config import app_logger
from core.services.scheduler_mgr import scheduler_mgr

log = app_logger


class PlaylistScheduling:
    """playlist 模块的「调度」子系统，所有 APScheduler 操作集中于此。"""

    _CRON_PREFIX = "playlist_cron_"
    _FILE_TIMER_PREFIX = "playlist_file_timer_"
    _FILE_ON_DEVICE_TIMER_PREFIX = "playlist_file_on_device_timer_"
    _DURATION_TIMER_PREFIX = "playlist_duration_timer_"
    _STOP_VERIFY_PREFIX = "playlist_stop_verify_"
    _GUARD_JOB_ID = "playlist_duration_guard"

    def __init__(
        self,
        playlist_raw_provider: Callable[[], Dict[str, Any]],
        devices_provider: Callable[[], Any],
        playing_playlists_provider: Callable[[], Set[str]],
        save_async: Callable[[], Any],
        on_play: Callable[..., Tuple[int, str]],
        on_stop: Callable[[str], Tuple[int, str]],
        on_file_timer_fire: Callable[[str], None],
    ) -> None:
        # provider 取 fresh 引用，避免 mgr 上 reload / 测试 fixture 重赋值导致引用过期
        self._playlist_raw_provider = playlist_raw_provider
        self._devices_provider = devices_provider
        self._playing_playlists_provider = playing_playlists_provider
        self._save_async = save_async
        self._on_play = on_play
        self._on_stop = on_stop
        self._on_file_timer_fire = on_file_timer_fire

        self._file_timers: Dict[str, str] = {}
        self._file_on_device_timers: Dict[str, str] = {}
        self._playlist_duration_timers: Dict[str, str] = {}
        self._scheduled_play_start_times: Dict[str, datetime.datetime] = {}

    # ===== cron =====

    def refresh_cron_job(self, playlist_id: str, playlist_data: Dict[str, Any]) -> None:
        try:
            job_id = f"{self._CRON_PREFIX}{playlist_id}"
            schedule = playlist_data.get("schedule", {})
            enabled = schedule.get("enabled", 0)
            cron_expression = schedule.get("cron", "").strip()

            if scheduler_mgr.get_job(job_id):
                scheduler_mgr.remove_job(job_id)

            if enabled != 1 or not cron_expression:
                return

            def cron_play_task(pid=playlist_id) -> None:
                p_name = self._playlist_raw_provider().get(pid, {}).get("name", "未知播放列表")
                try:
                    if pid in self._playing_playlists_provider():
                        log.info(
                            f"[PlaylistScheduling] 定时任务触发时播放列表正在播放中，跳过: {pid} - {p_name}")
                        return
                    code, msg = self._on_play(pid, force=False)
                    if code == 0:
                        log.info(
                            f"[PlaylistScheduling] 定时任务播放成功: {pid} - {p_name}")
                    else:
                        log.error(
                            f"[PlaylistScheduling] 定时任务播放失败: {pid} - {p_name}, {msg}")
                except Exception as e:
                    if isinstance(e, gevent.exceptions.LoopExit):  # pyright: ignore[reportAttributeAccessIssue]
                        log.warning(
                            f"[PlaylistScheduling] 定时任务执行后发生 gevent LoopExit (可忽略): {pid} - {p_name}")
                    else:
                        log.error(
                            f"[PlaylistScheduling] 定时任务执行异常: {pid} - {p_name}, {e}")

            success = scheduler_mgr.add_cron_job(
                func=cron_play_task, job_id=job_id, cron_expression=cron_expression)
            playlist_name = playlist_data.get("name", "未知播放列表")
            if success:
                log.info(
                    f"[PlaylistScheduling] 创建定时任务成功: {playlist_id}, {playlist_name}, cron: {cron_expression}")
            else:
                log.error(
                    f"[PlaylistScheduling] 创建定时任务失败: {playlist_id}, {playlist_name}, cron: {cron_expression}")
        except Exception as e:
            log.error(
                f"[PlaylistScheduling] refresh_cron_job error: id={playlist_id}, {e}", exc_info=True)
            raise

    # ===== duration guard =====

    def ensure_duration_guard_job(self) -> None:
        """确保播放列表时长守护任务已启动（每 30s 检查一次）。"""
        try:
            if scheduler_mgr.get_job(self._GUARD_JOB_ID):
                return

            def _guard_task() -> None:
                try:
                    now = datetime.datetime.now()
                    grace = timedelta(seconds=15)
                    playlist_raw = self._playlist_raw_provider()

                    # 1) 内存中的开始时间（在线触发的常规路径）
                    for pid, start_time in list(self._scheduled_play_start_times.items()):
                        schedule = (playlist_raw.get(pid, {}) or {}
                                    ).get("schedule", {}) or {}
                        duration_minutes = schedule.get("duration", 0)
                        if duration_minutes <= 0:
                            continue
                        planned_end = start_time + \
                            timedelta(minutes=duration_minutes)
                        self._force_stop_if_expired(
                            pid, planned_end, now, grace, source="内存开始时间")

                    # 2) RDS 固化的 duration_timer_at（进程重启 _scheduled_play_start_times 可能为空时兜底）
                    for pid, playlist_data in list(playlist_raw.items()):
                        if not playlist_data.get("isPlaying"):
                            continue
                        schedule = playlist_data.get("schedule", {}) or {}
                        if schedule.get("duration", 0) <= 0:
                            continue
                        dta = playlist_data.get("duration_timer_at")
                        if not dta:
                            continue
                        try:
                            end_dt = datetime.datetime.strptime(
                                str(dta).strip(), "%Y-%m-%d %H:%M:%S")
                        except (ValueError, TypeError):
                            continue
                        self._force_stop_if_expired(
                            pid, end_dt, now, grace, source="固化时间")
                except Exception as e:
                    log.error(
                        f"[PlaylistScheduling] 播放列表时长守护任务执行异常: {e}", exc_info=True)

            added = scheduler_mgr.add_interval_job(
                func=_guard_task, job_id=self._GUARD_JOB_ID, seconds=30)
            if added:
                log.info(
                    "[PlaylistScheduling] 启动播放列表时长守护任务成功: 每 30 秒检查一次超时播放列表")
            else:
                log.error("[PlaylistScheduling] 启动播放列表时长守护任务失败")
        except Exception as e:
            log.error(
                f"[PlaylistScheduling] 初始化播放列表时长守护任务异常: {e}", exc_info=True)

    # ===== reload 后恢复 =====

    def restore_timers_from_persistence(self) -> None:
        """reload / 冷启动后根据 RDS 中固化的定时器字段恢复 APScheduler 任务。"""
        if sys.platform != "linux":
            return
        playlist_raw = self._playlist_raw_provider()
        if not playlist_raw:
            return
        now = datetime.datetime.now()
        for pid, p_data in list(playlist_raw.items()):
            if not p_data.get("isPlaying"):
                continue
            if pid not in self._devices_provider():
                log.warning(
                    f"[PlaylistScheduling] reload 恢复定时器: 无设备映射，跳过 {pid}")
                continue
            self._playing_playlists_provider().add(pid)

            schedule = p_data.get("schedule") or {}
            dur_min = int(schedule.get("duration", 0) or 0)
            dta = p_data.get("duration_timer_at")
            if dur_min > 0 and dta:
                try:
                    end_dt = datetime.datetime.strptime(
                        str(dta).strip(), "%Y-%m-%d %H:%M:%S")
                    if end_dt <= now:
                        self._on_stop(pid)
                        continue
                    remaining_min = max(
                        (end_dt - now).total_seconds() / 60.0, 1.0 / 60.0)
                    self.start_playlist_duration_timer(
                        pid, remaining_min, start_at=end_dt - timedelta(minutes=dur_min))
                except (ValueError, TypeError) as e:
                    log.warning(
                        f"[PlaylistScheduling] reload 恢复 duration_timer_at 失败 {pid}: {e}")

            p_data = playlist_raw.get(pid)
            if not p_data or not p_data.get("isPlaying"):
                continue
            fta = p_data.get("file_timer_at")
            if fta:
                try:
                    file_end = datetime.datetime.strptime(
                        str(fta).strip(), "%Y-%m-%d %H:%M:%S")
                    if file_end <= now:
                        spawn(lambda p=pid: self._on_file_timer_fire(p))
                    else:
                        self.start_file_timer(
                            pid, (file_end - now).total_seconds())
                except (ValueError, TypeError) as e:
                    log.warning(
                        f"[PlaylistScheduling] reload 恢复 file_timer_at 失败 {pid}: {e}")
            else:
                log.warning(
                    f"[PlaylistScheduling] reload 恢复: isPlaying=True 但缺少 file_timer_at，无法恢复切歌定时器: {pid}")

    # ===== 孤儿清理 =====

    def cleanup_orphaned_jobs(self, valid_ids: Set[str]) -> None:
        """清理 APScheduler 上所有不属于 valid_ids 的 prefix 任务，以及自有 4 个 dict 中的孤儿。"""
        job_prefixes = [
            (self._CRON_PREFIX, "定时任务"),
            (self._FILE_TIMER_PREFIX, "文件定时器"),
            (self._FILE_ON_DEVICE_TIMER_PREFIX, "单次推播文件定时器"),
            (self._DURATION_TIMER_PREFIX, "播放列表时长定时器"),
            (self._STOP_VERIFY_PREFIX, "停止验证任务"),
        ]
        for job in scheduler_mgr.get_all_jobs():
            for prefix, name in job_prefixes:
                if job.id.startswith(prefix):
                    pid = job.id.replace(prefix, "", 1)
                    if pid not in valid_ids:
                        scheduler_mgr.remove_job(job.id)
                        log.info(f"[PlaylistScheduling] 清理孤立的{name}: {job.id}")
                    break

        for state_dict in (
            self._scheduled_play_start_times,
            self._file_timers,
            self._file_on_device_timers,
            self._playlist_duration_timers,
        ):
            for pid in list(state_dict.keys()):
                if pid not in valid_ids:
                    del state_dict[pid]

    # ===== file / on-device / playlist duration timers =====

    def start_file_timer(self, id: str, duration_seconds: float) -> None:
        """启动单个文件播放结束后的切歌定时器。"""
        job_id = f"{self._FILE_TIMER_PREFIX}{id}"
        if scheduler_mgr.get_job(job_id):
            scheduler_mgr.remove_job(job_id)

        def __play_next_task(pid=id) -> None:
            self._on_file_timer_fire(pid)

        run_date = datetime.datetime.now() + timedelta(seconds=duration_seconds)
        scheduler_mgr.add_date_job(
            func=__play_next_task, job_id=job_id, run_date=run_date)
        self._file_timers[id] = job_id
        playlist_raw = self._playlist_raw_provider()
        p_data = playlist_raw.get(id)
        if p_data is not None:
            p_data["file_timer_at"] = run_date.strftime("%Y-%m-%d %H:%M:%S")
            self._save_async()
        p_name = playlist_raw.get(id, {}).get("name", "未知播放列表")
        log.info(
            f"[PlaylistScheduling] 启动文件定时器: {id} - {p_name}, 将在 {duration_seconds} 秒后播放下一首")

    def start_file_on_device_timer(self, playlist_id: str, duration_seconds: float) -> None:
        """启动单次推播文件定时器，到时间后停止设备。"""
        job_id = f"{self._FILE_ON_DEVICE_TIMER_PREFIX}{playlist_id}"
        if scheduler_mgr.get_job(job_id):
            scheduler_mgr.remove_job(job_id)

        def _stop_device_task(pid=playlist_id) -> None:
            self.clear_file_on_device_timer(pid)
            devices = self._devices_provider()
            if pid not in devices:
                return
            stop_code, stop_msg = devices.safe_stop(pid)
            p_name = self._playlist_raw_provider().get(pid, {}).get("name", "未知播放列表")
            if stop_code == 0:
                log.info(
                    f"[PlaylistScheduling] 单次推播文件定时器触发，已停止设备: {pid} - {p_name}")
            else:
                log.warning(
                    f"[PlaylistScheduling] 单次推播文件定时器触发，停止设备失败: {pid} - {p_name}, {stop_msg}")

        run_date = datetime.datetime.now() + timedelta(seconds=duration_seconds)
        scheduler_mgr.add_date_job(
            func=_stop_device_task, job_id=job_id, run_date=run_date)
        self._file_on_device_timers[playlist_id] = job_id
        p_name = self._playlist_raw_provider().get(
            playlist_id, {}).get("name", "未知播放列表")
        log.info(
            f"[PlaylistScheduling] 启动单次推播文件定时器: {playlist_id} - {p_name}, 将在 {duration_seconds} 秒后停止设备")

    def start_playlist_duration_timer(self, id: str, duration_minutes: float, start_at: datetime.datetime | None = None) -> None:
        """启动播放列表整体时长限制定时器。

        Args:
            id: 播放列表 ID。
            duration_minutes: 时长（分钟），支持小数（reload 恢复剩余时间用）。
            start_at: 播放开始时间，默认 now；reload 恢复时传历史 start_time，供 duration guard 使用。
        """
        job_id = f"{self._DURATION_TIMER_PREFIX}{id}"
        playlist_raw = self._playlist_raw_provider()
        p_name = playlist_raw.get(id, {}).get("name", "未知播放列表")

        # 如果定时器已经存在，不要重置它（避免每次切歌都重置倒计时）
        if scheduler_mgr.get_job(job_id):
            log.debug(
                f"[PlaylistScheduling] 播放列表时长定时器已存在，跳过重启: {id} - {p_name}")
            return

        def stop_playlist_task(pid=id) -> None:
            pl_raw = self._playlist_raw_provider()
            p_name_inner = pl_raw.get(pid, {}).get("name", "未知播放列表")
            log.info(
                f"[PlaylistScheduling] 播放列表时长定时器触发: {pid} - {p_name_inner}")
            try:
                self.clear_playlist_duration_timer(pid)
                self.clear_file_timer(pid)
                self._scheduled_play_start_times.pop(pid, None)

                if pid not in self._playing_playlists_provider():
                    log.info(
                        f"[PlaylistScheduling] 播放列表时长定时器触发时播放列表已不在播放中，仅清理: {pid} - {p_name_inner}")
                    p_data = pl_raw.get(pid)
                    if p_data:
                        p_data.pop("duration_timer_at", None)
                        p_data.pop("file_timer_at", None)
                        self._save_async()
                    return

                code, msg = self._on_stop(pid)
                if code == 0:
                    log.info(
                        f"[PlaylistScheduling] 播放列表时长定时器停止播放成功: {pid} - {p_name_inner}")
                else:
                    log.error(
                        f"[PlaylistScheduling] 播放列表时长定时器停止播放失败: {pid} - {p_name_inner}, {msg}")
            except Exception as e:
                log.error(
                    f"[PlaylistScheduling] 播放列表时长定时器执行异常: {pid} - {p_name_inner}, {e}", exc_info=True)

        run_date = datetime.datetime.now() + timedelta(minutes=duration_minutes)
        scheduler_mgr.add_date_job(
            func=stop_playlist_task, job_id=job_id, run_date=run_date)
        self._playlist_duration_timers[id] = job_id
        self._scheduled_play_start_times[id] = start_at or datetime.datetime.now(
        )
        p_data = playlist_raw.get(id)
        if p_data is not None:
            p_data["duration_timer_at"] = run_date.strftime(
                "%Y-%m-%d %H:%M:%S")
            self._save_async()
        log.info(
            f"[PlaylistScheduling] 启动播放列表时长定时器: {id} - {p_name}, 将在 {duration_minutes} 分钟后停止播放")

    def schedule_one_shot(self, job_id: str, delay_seconds: float, func: Callable[..., Any]) -> None:
        """通用一次性任务（如 stop 后的 verify）。会先 idempotent 清掉同名旧任务。"""
        if scheduler_mgr.get_job(job_id):
            scheduler_mgr.remove_job(job_id)
        run_date = datetime.datetime.now() + timedelta(seconds=delay_seconds)
        scheduler_mgr.add_date_job(func=func, job_id=job_id, run_date=run_date)

    # ===== timer 清理 =====

    def clear_all_for(self, id: str) -> None:
        """清掉该 playlist 的全部调度状态（4 个 timer + start time），用于 stop/cleanup。"""
        self._drop_timer(self._file_timers, id)
        self._drop_timer(self._file_on_device_timers, id)
        self._drop_timer(self._playlist_duration_timers, id)
        self._scheduled_play_start_times.pop(id, None)

    def clear_file_timer(self, id: str) -> None:
        self._drop_timer(self._file_timers, id)

    def clear_file_on_device_timer(self, id: str) -> None:
        self._drop_timer(self._file_on_device_timers, id)

    def clear_playlist_duration_timer(self, id: str) -> None:
        self._drop_timer(self._playlist_duration_timers, id)

    def _drop_timer(self, timer_dict: Dict[str, str], id: str) -> None:
        job_id = timer_dict.pop(id, None)
        if job_id and scheduler_mgr.get_job(job_id):
            scheduler_mgr.remove_job(job_id)

    def _force_stop_if_expired(
        self,
        pid: str,
        planned_end: datetime.datetime,
        now: datetime.datetime,
        grace: timedelta,
        source: str,
    ) -> None:
        if now < planned_end + grace:
            return
        p_name = (self._playlist_raw_provider().get(
            pid, {}) or {}).get("name", "未知播放列表")
        log.warning(f"[PlaylistScheduling] 播放列表时长守护任务({source})检测到超时，强制停止: "
                    f"{pid} - {p_name}, 计划结束: {planned_end}, 当前: {now}")
        code, msg = self._on_stop(pid)
        if code != 0:
            log.error(
                f"[PlaylistScheduling] 播放列表时长守护任务({source})强制停止失败: {pid} - {p_name}, {msg}")

    # ===== read-only accessors（兼容现有测试直接读 dict 的写法）=====

    @property
    def scheduled_play_start_times(self) -> Dict[str, datetime.datetime]:
        return self._scheduled_play_start_times

    @property
    def playlist_duration_timers(self) -> Dict[str, str]:
        return self._playlist_duration_timers
