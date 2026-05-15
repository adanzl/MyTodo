from typing import Optional

from flask import json


class Subtask:
    """日程子任务数据类，对应前端 Subtask 类型"""

    def __init__(self):
        self.id: int = -1
        self.title: Optional[str] = ""
        self.order: Optional[int] = 0
        self.score: Optional[int] = None
        self.imgIds: list = []  # 图片id列表

        # 完成状态字段（来自 t_schedule_save）
        self.state: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> 'Subtask':
        """从字典创建实例"""
        instance = cls()
        instance.id = data.get('id', -1)
        # 兼容 name 和 title 字段
        instance.title = data.get('name') or data.get('title', '')
        instance.order = data.get('order', 0)
        instance.score = data.get('score')
        instance.imgIds = data.get('imgIds', [])
        return instance
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.title,
            'order': self.order,
            'score': self.score,
            'imgIds': self.imgIds,
            'state': self.state,
        }


class ScheduleData:
    """日程数据类，对应前端 ScheduleData 类型"""

    def __init__(self):
        # 基础字段（来自 t_schedule）
        self.id: int = -1  # 日程ID
        self.title: str = ""  # 标题
        self.startTs: Optional[str] = None  # 开始时间戳
        self.endTs: Optional[str] = None  # 结束时间戳
        self.allDay: int = 1  # 是否全天：0-否，1-是
        self.reminder: int = 0  # 提醒时间（分钟）
        self.repeat: int = 0  # 重复类型：0-无，1-每天，2-每周，3-每月，4-每年，5-工作日，6-周末，999-自定义
        self.repeatData: dict = {}  # 重复规则数据
        self.repeatEndTs: Optional[str] = None  # 重复结束时间
        self.color: int = 0  # 颜色索引
        self.priority: int = -1  # 优先级
        self.groupId: int = -1  # 分组ID
        self.order: int = 0  # 排序序号
        self.score: Optional[int] = None  # 积分
        self.subtasks: list[Subtask] = []  # 子任务列表
        self.userId: Optional[int] = None  # 用户ID

        # 完成状态字段（来自 t_schedule_save）
        self.state: int = 0  # 完成状态：0-未完成，1-已完成
        self.saveScore: Optional[int] = None  # 实际获得积分

    @classmethod
    def from_db_rows(cls, schedule_row: dict, save_row: Optional[dict] = None) -> 'ScheduleData':
        """从数据库行创建实例，合并 t_schedule 和 t_schedule_save 数据"""
        instance = cls()
        # 从 t_schedule 获取基础数据
        instance.id = schedule_row.get('id', -1)
        instance.title = schedule_row.get('title', '') or ''
        instance.startTs = schedule_row.get('start_ts')
        instance.endTs = schedule_row.get('end_ts')
        instance.allDay = schedule_row.get('all_day', 1) if schedule_row.get('all_day') is not None else 1
        instance.reminder = schedule_row.get('reminder', 0) if schedule_row.get('reminder') is not None else 0
        instance.repeat = schedule_row.get('repeat', 0) if schedule_row.get('repeat') is not None else 0
        instance.repeatData = json.loads(schedule_row['repeat_data']) if schedule_row.get('repeat_data') else {}
        instance.repeatEndTs = schedule_row.get('repeat_end_ts')
        instance.color = schedule_row.get('color', 0) if schedule_row.get('color') is not None else 0
        instance.priority = schedule_row.get('priority', -1) if schedule_row.get('priority') is not None else -1
        instance.groupId = schedule_row.get('group_id', -1) if schedule_row.get('group_id') is not None else -1
        instance.order = schedule_row.get('order_idx', 0) if schedule_row.get('order_idx') is not None else 0
        instance.score = schedule_row.get('score')

        # 解析子任务列表
        subtasks_raw = json.loads(schedule_row['subtasks']) if schedule_row.get('subtasks') else []
        instance.subtasks = [Subtask.from_dict(st_data) for st_data in subtasks_raw]

        instance.userId = schedule_row.get('user_id')

        # 从 t_schedule_save 获取完成状态和覆盖数据
        if save_row:
            instance.state = save_row.get('state', 0) if save_row.get('state') is not None else 0
            instance.saveScore = save_row.get('score')

            # 应用覆盖字段
            override_data = json.loads(save_row['schedule_override']) if save_row.get('schedule_override') else None
            if override_data:
                instance.apply_override(override_data)

            # 应用子任务完成状态
            save_subtasks = json.loads(save_row['subtasks']) if save_row.get('subtasks') else {}
            if save_subtasks and isinstance(save_subtasks, dict):
                for st in instance.subtasks:
                    if str(st.id) in save_subtasks or st.id in save_subtasks:
                        st.state = save_subtasks.get(str(st.id), save_subtasks.get(st.id, 0))

        return instance

    def apply_override(self, override_data: dict):
        """应用覆盖字段"""
        if not override_data:
            return

        if override_data.get('title') is not None:
            self.title = override_data['title']
        if override_data.get('color') is not None:
            self.color = override_data['color']
        if override_data.get('priority') is not None:
            self.priority = override_data['priority']
        if override_data.get('groupId') is not None:
            self.groupId = override_data['groupId']
        if override_data.get('order') is not None:
            self.order = override_data['order']
        if override_data.get('score') is not None:
            self.score = override_data['score']
        if override_data.get('subtasks') is not None:
            # 解析覆盖的子任务列表
            override_subtasks_raw = override_data['subtasks']
            if isinstance(override_subtasks_raw, list):
                self.subtasks = [Subtask.from_dict(st_data) for st_data in override_subtasks_raw]

    def set_save_info(self, state: int, subtask_states: dict, score: Optional[int]):
        """设置存档信息"""
        self.state = state
        self.saveScore = score

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'startTs': self.startTs,
            'endTs': self.endTs,
            'allDay': self.allDay,
            'reminder': self.reminder,
            'repeat': self.repeat,
            'repeatData': self.repeatData,
            'repeatEndTs': self.repeatEndTs,
            'color': self.color,
            'priority': self.priority,
            'groupId': self.groupId,
            'order': self.order,
            'score': self.score,
            'subtasks': [st.to_dict() for st in self.subtasks],
            'userId': self.userId,
            'state': self.state,
            'saveScore': self.saveScore
        }


class ScheduleSave:
    """日程存档数据类，对应前端 ScheduleSave 类型"""
    def __init__(self):
        self.id: int = -1
        self.date: str = ""
        self.scheduleId: int = -1
        self.state: int = 0
        self.subtasks: dict = {}
        self.score: Optional[int] = None
        self.scheduleOverride: Optional[ScheduleData] = None
