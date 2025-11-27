"""
Playlist 业务相关工具函数
"""

import datetime
import json
import time
from datetime import timedelta
from typing import Dict, Any, List, Optional

from core.db import rds_mgr
from core.device.agent import DeviceAgent
from core.device.dlna import DlnaDev
from core.log_config import root_logger
from core.scheduler import get_scheduler

log = root_logger()

PLAYLIST_RDS_FULL_KEY = f"schedule_play:playlist_collection"
DEFAULT_PLAYLIST_NAME = "默认播放列表"
DEVICE_TYPES = {"device_agent", "bluetooth", "dlna"}


def _generate_playlist_id() -> str:
    return f"pl_{int(time.time() * 1000)}"

_TS = lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _create_device(node):
    """
    创建设备对象
    注意：bluetooth 类型也使用 DeviceAgent，因为蓝牙播放通过 device_agent 服务实现
    """
    ret = {"node": node, "obj": None}
    if node["type"] == "agent":
        ret["obj"] = DeviceAgent(node["address"])
    elif node["type"] == "bluetooth":
        # 蓝牙设备也使用 DeviceAgent，因为播放通过 device_agent 服务实现
        ret["obj"] = DeviceAgent(node["address"])
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

        # 存储正在轮询的播放列表ID集合
        self._polling_playlists = set()
        # 轮询间隔（秒）- 改为1秒以更及时检测播放完成
        self._polling_interval = 1
        # 存储定时任务触发的播放开始时间 {playlist_id: start_time}
        self._scheduled_play_start_times = {}

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
        """刷新设备映射和定时任务"""
        self.device_map = {}
        scheduler = get_scheduler()
        
        if self.playlist_raw:
            for p_id in self.playlist_raw:
                playlist_data = self.playlist_raw[p_id]
                # 创建设备映射
                self.device_map[p_id] = _create_device(playlist_data.get("device", {}))
                
                # 刷新定时任务
                self._refresh_cron_job(p_id, playlist_data)
        
        # 清理不存在的播放列表对应的定时任务
        self._cleanup_orphaned_cron_jobs()
    
    def _refresh_cron_job(self, playlist_id: str, playlist_data: Dict[str, Any]):
        """
        刷新单个播放列表的 cron 定时任务
        :param playlist_id: 播放列表ID
        :param playlist_data: 播放列表数据
        """
        scheduler = get_scheduler()
        job_id = f"playlist_cron_{playlist_id}"
        
        schedule = playlist_data.get("schedule", {})
        enabled = schedule.get("enabled", 0)
        cron_expression = schedule.get("cron", "").strip()
        
        # 如果定时任务已存在，先移除
        existing_job = scheduler.get_job(job_id)
        if existing_job:
            scheduler.remove_job(job_id)
            log.info(f"[PlaylistMgr] 移除已存在的定时任务: {job_id}")
        
        # 如果未启用或 cron 表达式为空，不创建任务
        if enabled != 1 or not cron_expression:
            log.debug(f"[PlaylistMgr] 播放列表 {playlist_id} 的定时任务未启用或 cron 表达式为空，跳过创建")
            return
        
        # 创建定时任务函数（使用默认参数确保闭包正确捕获变量）
        def cron_play_task(pid=playlist_id):
            """定时任务：播放指定的播放列表"""
            try:
                log.info(f"[PlaylistMgr] 定时任务触发，开始播放播放列表: {pid}")
                
                # 播放播放列表
                code, msg = self.play(pid)
                if code == 0:
                    log.info(f"[PlaylistMgr] 定时任务播放成功: {pid}")
                    # 记录定时任务触发的播放开始时间
                    self._scheduled_play_start_times[pid] = datetime.datetime.now()
                else:
                    log.error(f"[PlaylistMgr] 定时任务播放失败: {pid}, 错误: {msg}")
            except Exception as e:
                log.error(f"[PlaylistMgr] 定时任务执行异常: {pid}, 错误: {e}")
        
        # 添加 cron 任务
        success = scheduler.add_cron_job(
            func=cron_play_task,
            job_id=job_id,
            cron_expression=cron_expression
        )
        
        if success:
            log.info(f"[PlaylistMgr] 创建播放列表定时任务成功: {playlist_id}, cron: {cron_expression}")
        else:
            log.error(f"[PlaylistMgr] 创建播放列表定时任务失败: {playlist_id}, cron: {cron_expression}")
    
    def _cleanup_orphaned_cron_jobs(self):
        """
        清理孤立的定时任务（对应的播放列表已不存在）
        """
        scheduler = get_scheduler()
        all_jobs = scheduler.get_all_jobs()
        
        # 获取所有播放列表ID
        playlist_ids = set(self.playlist_raw.keys() if self.playlist_raw else [])
        
        # 检查所有任务，删除不存在的播放列表对应的任务
        for job in all_jobs:
            job_id = job.id
            # 检查是否是播放列表的 cron 任务
            if job_id.startswith("playlist_cron_"):
                playlist_id = job_id.replace("playlist_cron_", "", 1)
                if playlist_id not in playlist_ids:
                    scheduler.remove_job(job_id)
                    log.info(f"[PlaylistMgr] 清理孤立的定时任务: {job_id} (播放列表 {playlist_id} 不存在)")
        
        # 清理不存在的播放列表的开始时间记录
        for playlist_id in list(self._scheduled_play_start_times.keys()):
            if playlist_id not in playlist_ids:
                del self._scheduled_play_start_times[playlist_id]

    def play(self, id: str) -> tuple[int, str]:
        """
        播放播放列表中当前索引的文件
        对于 DLNA 设备，启动轮询任务自动播放下一首
        """
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
        device = device_obj["obj"]

        # 播放当前文件（使用统一接口）
        code, msg = device.play(file_path)
        if code != 0:
            return code, msg

        # 启动轮询任务自动播放下一首（列表循环播放）
        # 只对支持状态查询的设备启动轮询（通过检查 get_transport_info 是否可用）
        transport_code, _ = device.get_transport_info()
        if transport_code == 0:
            self._start_polling(id)

        return 0, "播放成功"

    def play_next(self, id: str) -> tuple[int, str]:
        """
        播放下一首
        更新索引并播放下一首文件
        """
        if not self.playlist_raw or id not in self.playlist_raw:
            return -1, "播放列表不存在"

        playlist_data = self.playlist_raw[id]
        files, current_index = playlist_data.get("files", []), playlist_data.get("current_index", 0)

        if not files:
            return -1, "播放列表为空"

        # 更新索引
        next_index = (current_index + 1) % len(files)
        playlist_data["current_index"] = next_index
        playlist_data["updated_time"] = _TS()

        # 保存播放列表
        rds_mgr.set(PLAYLIST_RDS_FULL_KEY, json.dumps(self.playlist_raw, ensure_ascii=False))

        # 播放下一首（会自动启动轮询）
        code, msg = self.play(id)
        if code != 0:
            return -1, msg

        return 0, "播放下一首成功"

    def play_pre(self, id: str) -> tuple[int, str]:
        """
        播放上一首
        更新索引并播放上一首文件
        """
        if not self.playlist_raw or id not in self.playlist_raw:
            return -1, "播放列表不存在"

        playlist_data = self.playlist_raw[id]
        files, current_index = playlist_data.get("files", []), playlist_data.get("current_index", 0)

        if not files:
            return -1, "播放列表为空"

        # 更新索引
        prev_index = (current_index - 1) % len(files)
        playlist_data["current_index"] = prev_index
        playlist_data["updated_time"] = _TS()

        # 保存播放列表
        rds_mgr.set(PLAYLIST_RDS_FULL_KEY, json.dumps(self.playlist_raw, ensure_ascii=False))

        # 播放上一首（会自动启动轮询）
        code, msg = self.play(id)
        if code != 0:
            return -1, msg

        return 0, "播放上一首成功"

    def stop(self, id: str) -> tuple[int, str]:
        """
        停止播放
        停止播放并停止轮询任务，同时清除定时任务触发的播放开始时间记录
        """
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
        """
        启动轮询任务，定期检查播放状态并自动播放下一首
        :param id: 播放列表ID
        """
        if id in self._polling_playlists:
            # 已经在轮询中，不需要重复启动
            return

        device_obj = self.device_map.get(id)
        if device_obj is None:
            return

        device = device_obj["obj"]
        if device is None:
            return

        # 检查设备是否支持状态查询（使用统一接口）
        transport_code, _ = device.get_transport_info()
        if transport_code != 0:
            # 设备不支持状态查询，不启动轮询
            log.debug(f"[PlaylistMgr] 设备不支持状态查询，不启动轮询: {id}")
            return

        # 创建轮询任务函数
        def poll_task():
            if id not in self._polling_playlists:
                return

            # 检查播放状态并自动播放下一首（每秒检查一次播放位置）
            code, msg = self._check_and_auto_play_next(id)
            if code == 0:
                log.info(f"[PlaylistMgr] 自动播放下一首成功: {id}")
            # code == -1 表示未播放完成，继续轮询（不输出日志避免日志过多）

        # 添加间隔任务
        job_id = f"playlist_poll_{id}"
        scheduler = get_scheduler()
        scheduler.add_interval_job(
            func=poll_task,
            job_id=job_id,
            seconds=self._polling_interval
        )

        self._polling_playlists.add(id)
        log.info(f"[PlaylistMgr] 启动播放列表轮询任务: {id}, 间隔: {self._polling_interval}秒")

    def _stop_polling(self, id: str):
        """
        停止轮询任务
        :param id: 播放列表ID
        """
        if id not in self._polling_playlists:
            return

        job_id = f"playlist_poll_{id}"
        scheduler = get_scheduler()
        scheduler.remove_job(job_id)

        self._polling_playlists.discard(id)
        log.info(f"[PlaylistMgr] 停止播放列表轮询任务: {id}")

    def _check_and_auto_play_next(self, id: str) -> tuple[int, str]:
        """
        检查播放状态，如果播放完成则自动播放下一首
        每秒检查一次播放位置，如果超过当前曲目时间则触发播放下一首
        同时检查定时任务触发的播放是否超过配置的播放时长限制
        使用统一设备接口，不区分设备类型
        :return: (错误码, 消息) 0 表示已自动播放下一首或已停止，-1 表示未播放或出错
        """
        if not self.playlist_raw or id not in self.playlist_raw:
            return -1, "播放列表不存在"

        playlist_data = self.playlist_raw[id]
        device_obj = self.device_map.get(id)
        if device_obj is None:
            return -1, "设备不存在或未初始化"

        device = device_obj["obj"]
        if device is None:
            return -1, "设备对象未初始化"

        # 检查定时任务触发的播放时长限制
        if id in self._scheduled_play_start_times:
            schedule = playlist_data.get("schedule", {})
            duration_minutes = schedule.get("duration", 0)
            
            if duration_minutes > 0:
                start_time = self._scheduled_play_start_times[id]
                elapsed_time = datetime.datetime.now() - start_time
                elapsed_minutes = elapsed_time.total_seconds() / 60
                
                # 如果超过配置的播放时长，停止播放
                if elapsed_minutes >= duration_minutes:
                    log.info(f"[PlaylistMgr] 定时任务播放时长限制到达 ({elapsed_minutes:.1f}分钟 >= {duration_minutes}分钟)，停止播放: {id}")
                    # 清除开始时间记录
                    del self._scheduled_play_start_times[id]
                    # 停止播放
                    code, msg = self.stop(id)
                    if code == 0:
                        return 0, "播放时长限制到达，已停止播放"
                    else:
                        return code, msg

        # 获取播放位置信息
        pos_code, pos_info = device.get_position_info()
        if pos_code != 0:
            return -1, "无法获取播放位置信息"

        track_duration = pos_info.get("track_duration", "00:00:00")
        rel_time = pos_info.get("rel_time", "00:00:00")

        def time_to_seconds(time_str):
            """将时间字符串（如 '00:03:45'）转换为秒数"""
            parts = time_str.split(':')
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return 0

        try:
            duration_sec = time_to_seconds(track_duration)
            rel_sec = time_to_seconds(rel_time)

            # 如果总时长无效，跳过检查
            if duration_sec <= 0:
                return -1, "无法获取有效的曲目时长"

            # 检查播放位置是否超过曲目总时长
            # 如果已播放时间 >= 总时长，认为是播放完成，自动播放下一首
            if rel_sec >= duration_sec:
                # log.info(f"[PlaylistMgr] 检测到播放位置超过曲目时长 ({rel_sec}s >= {duration_sec}s)，自动播放下一首: {id}")
                return self.play_next(id)

            # 如果播放位置接近总时长（在最后1秒内），也触发下一首
            # 这样可以避免设备单曲循环的问题
            if rel_sec >= duration_sec - 1:
                # log.info(f"[PlaylistMgr] 检测到播放位置接近曲目末尾 ({rel_sec}s >= {duration_sec - 1}s)，自动播放下一首: {id}")
                return self.play_next(id)

        except Exception as e:
            log.warning(f"[PlaylistMgr] Error checking playback completion: {e}")

        return -1, "播放未完成"


playlist_mgr = PlaylistMgr()
