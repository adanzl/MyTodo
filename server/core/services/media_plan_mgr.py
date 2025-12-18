import datetime
import json
import sys
import threading
from datetime import timedelta
from typing import Any, Dict, List, Optional

from core.utils import get_media_duration, check_cron_will_trigger_today
from core.db import rds_mgr
from core.device import create_device
from core.log_config import root_logger
from core.services.scheduler_mgr import scheduler_mgr
from core.utils import time_to_seconds

log = root_logger()

MEDIA_PLAN_RDS_FULL_KEY = "schedule_play:media_plan_collection"
DEFAULT_PLAN_NAME = "默认计划"
DEVICE_TYPES = {"device_agent", "bluetooth", "dlna", "mi"}

_TS = lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class MediaPlanMgr:

    def __init__(self):
        self._scheduled_play_start_times = {}  # 定时任务播放开始时间（用于duration限制）
        self._file_timers = {}  # 文件播放定时器 {plan_id: job_id}
        self._plan_duration_timers = {}  # 计划时长定时器 {plan_id: job_id}
        self._playing_plans = set()  # 正在播放的计划ID集合
        self._plan_raw = {}  # 计划数据
        self._device_map = {}  # 设备映射
        self._play_state = {}  # 播放状态跟踪 {plan_id: {'pre_list_index': int, 'file_index': int}}
        self._needs_reload = False  # 标记是否需要重新从 RDS 加载
        self.reload()

    def get_plan(self, id: str | None = None) -> Dict[str, Dict[str, Any]]:
        """
        获取计划
        :param id: 计划ID，如果为None则返回所有计划
        :return: 计划字典，格式为 {plan_id: plan_data}
        """
        if self._needs_reload:
            log.info(f"[MediaPlanMgr] 需要重新加载，再次尝试从 RDS 加载")
            self.reload()

        if id is None:
            result = self._plan_raw
        else:
            plan_data = self._plan_raw.get(id)
            if plan_data is None:
                return {}
            result = {id: plan_data}

        # 为正在播放的计划添加播放状态信息
        for plan_id, plan_data in result.items():
            if plan_id in self._play_state:
                play_state = self._play_state[plan_id]
                plan_data["pre_list_index"] = play_state.get("pre_list_index", -1)
                plan_data["file_index"] = play_state.get("file_index", -1)
            else:
                plan_data["pre_list_index"] = -1
                plan_data["file_index"] = -1

        return result

    def _save_plan_to_rds(self):
        """保存计划到 RDS"""
        rds_mgr.set(MEDIA_PLAN_RDS_FULL_KEY, json.dumps(self._plan_raw, ensure_ascii=False))

    def save_plan(self, collection: Dict[str, Any]) -> int:
        """
        保存整个计划集合
        :param collection: 计划集合字典，格式为 {plan_id: plan_data}
        """
        self._plan_raw = collection
        self._save_plan_to_rds()
        # 更新设备映射和定时任务
        self._refresh_device_map()
        self._refresh_all_cron_jobs()
        return 0

    def update_single_plan(self, plan_data: Dict[str, Any]) -> int:
        """
        更新单个计划
        :param plan_data: 计划数据，必须包含 id 字段
        :return: 0 表示成功，-1 表示失败
        """
        if not plan_data or not isinstance(plan_data, dict):
            return -1
        
        plan_id = plan_data.get("id")
        if not plan_id:
            log.error("[MediaPlanMgr] 更新单个计划失败: plan_data 中缺少 id 字段")
            return -1
        
        # 如果计划不存在，创建新计划
        if plan_id not in self._plan_raw:
            log.info(f"[MediaPlanMgr] 计划 {plan_id} 不存在，将创建新计划")
        
        # 更新计划数据（合并现有数据）
        if plan_id in self._plan_raw:
            # 合并更新，保留原有字段
            existing_plan = self._plan_raw[plan_id]
            existing_plan.update(plan_data)
            self._plan_raw[plan_id] = existing_plan
        else:
            # 新计划
            self._plan_raw[plan_id] = plan_data
        
        self._save_plan_to_rds()
        # 更新设备映射和定时任务
        self._refresh_device_map()
        self._refresh_all_cron_jobs()
        return 0

    def reload(self) -> int:
        if sys.platform != "linux":
            log.warning(f"[MediaPlanMgr] Reload not supported on non-linux platforms : {sys.platform}")
            if not hasattr(self, '_plan_raw'):
                self._plan_raw = {}
            if not hasattr(self, '_device_map'):
                self._device_map = {}
            self._needs_reload = False
            return 0

        try:
            raw = rds_mgr.get(MEDIA_PLAN_RDS_FULL_KEY)
            if raw:
                self._plan_raw = json.loads(raw)
            else:
                self._plan_raw = {}
            log.info(f"[MediaPlanMgr] Reloaded {len(self._plan_raw)} plans from RDS")
            self._refresh_device_map()
            self._refresh_all_cron_jobs()
            self._needs_reload = False
            return 0
        except Exception as e:
            log.error(f"[MediaPlanMgr] Reload error: {e}")
            self._plan_raw = {}
            self._needs_reload = False
            return -1

    def _refresh_device_map(self):
        """刷新设备映射"""
        self._device_map = {}
        for plan_id, plan_data in self._plan_raw.items():
            device = plan_data.get("device")
            if device and device.get("address"):
                device_type = device.get("type") or plan_data.get("device_type", "dlna")
                if device_type in DEVICE_TYPES:
                    self._device_map[plan_id] = create_device({
                        "type": device_type,
                        "address": device.get("address"),
                        "name": device.get("name")
                    })

    def _refresh_all_cron_jobs(self):
        """刷新所有计划的定时任务"""
        for plan_id, plan_data in self._plan_raw.items():
            self._refresh_cron_job(plan_id, plan_data)

    def _refresh_cron_job(self, plan_id: str, plan_data: Dict[str, Any]):
        """刷新单个计划的定时任务"""
        scheduler = scheduler_mgr
        job_id = f"media_plan_cron_{plan_id}"
        schedule = plan_data.get("schedule", {})
        enabled = schedule.get("enabled", 0)
        cron_expression = schedule.get("cron", "").strip()

        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        if enabled != 1 or not cron_expression:
            return

        def cron_play_task(pid=plan_id):
            try:
                p_name = self._plan_raw.get(pid, {}).get("name", "未知计划")
                # 检查计划是否正在播放中
                if pid in self._playing_plans:
                    log.info(f"[MediaPlanMgr] 定时任务触发时计划正在播放中，跳过播放任务: {pid} - {p_name}")
                    return

                # 如果不在播放中，正常启动播放
                code, msg = self.play(pid, force=False)
                if code == 0:
                    self._scheduled_play_start_times[pid] = datetime.datetime.now()
                    log.info(f"[MediaPlanMgr] 定时任务播放成功: {pid} - {p_name}")
                else:
                    log.error(f"[MediaPlanMgr] 定时任务播放失败: {pid} - {p_name}, {msg}")
            except Exception as e:
                log.error(f"[MediaPlanMgr] 定时任务执行异常: {pid} - {p_name}, {e}")

        success = scheduler.add_cron_job(func=cron_play_task, job_id=job_id, cron_expression=cron_expression)
        plan_name = plan_data.get("name", "未知计划")
        if not success:
            log.error(f"[MediaPlanMgr] 创建定时任务失败: {plan_id}, {plan_name}, cron: {cron_expression}")

    def _get_active_file_list(self, plan_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据当前星期几获取激活的文件列表（前置列表+正式列表）
        :param plan_data: 计划数据
        :return: 文件列表
        """
        today_weekday = datetime.datetime.now().weekday()  # 0=周一, 6=周日
        # 转换为前端格式：1=周一, 7=周日
        # Python weekday(): 0=周一, 1=周二, ..., 6=周日
        # 前端格式: 1=周一, 2=周二, ..., 7=周日
        current_weekday = today_weekday + 1  # 0->1(周一), 6->7(周日)

        active_files = []
        pre_lists = plan_data.get("pre_lists", [])

        # 收集所有激活的前置列表
        for pre_list in pre_lists:
            weekdays = pre_list.get("weekdays", [])
            if current_weekday in weekdays:
                files = pre_list.get("files", [])
                active_files.extend(files)

        # 添加正式列表
        main_list = plan_data.get("main_list", {})
        main_files = main_list.get("files", [])
        active_files.extend(main_files)

        return active_files

    def play(self, plan_id: str, force: bool = False) -> tuple[int, str]:
        """
        播放计划
        :param plan_id: 计划ID
        :param force: 是否强制播放（即使正在播放也重新开始）
        :return: (code, msg)
        """
        if plan_id not in self._plan_raw:
            return -1, f"计划 {plan_id} 不存在"

        plan_data = self._plan_raw[plan_id]

        # 如果正在播放且不强制，返回错误
        if plan_id in self._playing_plans and not force:
            return -1, "计划正在播放中"

        # 停止之前的播放
        if plan_id in self._playing_plans:
            self.stop(plan_id)

        # 获取设备
        device_info = self._device_map.get(plan_id)
        if not device_info or not device_info.get("obj"):
            return -1, "设备未配置或不可用"

        device_obj = device_info["obj"]

        # 获取激活的文件列表
        file_list = self._get_active_file_list(plan_data)

        if not file_list:
            return -1, "没有可播放的文件"

        # 标记为正在播放
        self._playing_plans.add(plan_id)
        self._play_state[plan_id] = {
            "pre_list_index": 0,
            "file_index": 0
        }

        # 开始播放第一个文件
        self._play_next_file(plan_id, file_list, 0)

        # 检查是否有时长限制
        schedule = plan_data.get("schedule", {})
        duration_minutes = schedule.get("duration", 0)
        if duration_minutes > 0:
            self._start_plan_duration_timer(plan_id, duration_minutes)

        return 0, "播放成功"

    def _play_next_file(self, plan_id: str, file_list: List[Dict[str, Any]], file_index: int):
        """播放文件列表中的下一个文件"""
        if plan_id not in self._playing_plans:
            return

        if file_index >= len(file_list):
            # 播放完成
            self.stop(plan_id)
            return

        file_item = file_list[file_index]
        file_uri = file_item.get("uri")

        if not file_uri:
            # 跳过空文件，播放下一个
            self._play_next_file(plan_id, file_list, file_index + 1)
            return

        # 更新播放状态
        self._play_state[plan_id]["file_index"] = file_index

        # 获取设备
        device_info = self._device_map.get(plan_id)
        if not device_info or not device_info.get("obj"):
            log.error(f"[MediaPlanMgr] 设备不可用: {plan_id}")
            self.stop(plan_id)
            return

        device_obj = device_info["obj"]

        try:
            # 播放文件
            device_obj.play(file_uri)
            log.info(f"[MediaPlanMgr] 开始播放: {plan_id}, 文件 {file_index + 1}/{len(file_list)}: {file_uri}")

            # 获取文件时长
            duration = file_item.get("duration")
            if not duration:
                duration = get_media_duration(file_uri)
                if duration:
                    file_item["duration"] = duration

            if duration and duration > 0:
                # 设置定时器，在文件播放完成后播放下一个
                scheduler = scheduler_mgr
                job_id = f"media_plan_file_timer_{plan_id}"
                if scheduler.get_job(job_id):
                    scheduler.remove_job(job_id)

                def play_next_task(pid=plan_id, flist=file_list, fidx=file_index):
                    if pid in self._playing_plans:
                        self._play_next_file(pid, flist, fidx + 1)

                run_date = datetime.datetime.now() + timedelta(seconds=duration)
                scheduler.add_date_job(func=play_next_task, job_id=job_id, run_date=run_date)
                self._file_timers[plan_id] = job_id
            else:
                # 没有时长信息，立即播放下一个（可能有问题，但继续尝试）
                log.warning(f"[MediaPlanMgr] 文件没有时长信息: {file_uri}")
                self._play_next_file(plan_id, file_list, file_index + 1)

        except Exception as e:
            log.error(f"[MediaPlanMgr] 播放文件失败: {plan_id}, {file_uri}, {e}")
            # 播放失败，尝试下一个文件
            self._play_next_file(plan_id, file_list, file_index + 1)

    def stop(self, plan_id: str) -> tuple[int, str]:
        """停止播放计划"""
        if plan_id not in self._playing_plans:
            return 0, "计划未在播放"

        # 清除定时器
        self._clear_timer(plan_id, self._file_timers, "media_plan_file_timer_")
        self._clear_timer(plan_id, self._plan_duration_timers, "media_plan_duration_timer_")

        # 停止设备播放
        device_info = self._device_map.get(plan_id)
        if device_info and device_info.get("obj"):
            try:
                device_info["obj"].stop()
            except Exception as e:
                log.error(f"[MediaPlanMgr] 停止设备播放失败: {plan_id}, {e}")

        # 清除播放状态
        self._playing_plans.discard(plan_id)
        self._play_state.pop(plan_id, None)
        self._scheduled_play_start_times.pop(plan_id, None)

        log.info(f"[MediaPlanMgr] 停止播放: {plan_id}")
        return 0, "停止成功"

    def _clear_timer(self, id: str, timer_dict: Dict[str, str], job_prefix: str):
        """清除定时器"""
        job_id = timer_dict.get(id)
        if job_id:
            scheduler = scheduler_mgr
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
            del timer_dict[id]

    def _start_plan_duration_timer(self, id: str, duration_minutes: int):
        """启动计划时长限制定时器"""
        scheduler = scheduler_mgr
        job_id = f"media_plan_duration_timer_{id}"
        p_name = self._plan_raw.get(id, {}).get("name", "未知计划")

        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        def stop_plan_task(pid=id):
            p_name = self._plan_raw.get(pid, {}).get("name", "未知计划")
            log.info(f"[MediaPlanMgr] 计划时长定时器触发: {pid} - {p_name}")
            self._clear_timer(pid, self._plan_duration_timers, "media_plan_duration_timer_")
            self._scheduled_play_start_times.pop(pid, None)
            self.stop(pid)

        run_date = datetime.datetime.now() + timedelta(minutes=duration_minutes)
        scheduler.add_date_job(func=stop_plan_task, job_id=job_id, run_date=run_date)
        self._plan_duration_timers[id] = job_id
        log.info(f"[MediaPlanMgr] 启动计划时长定时器: {id} - {p_name}, 将在 {duration_minutes} 分钟后停止播放")


# 全局实例
media_plan_mgr = MediaPlanMgr()
