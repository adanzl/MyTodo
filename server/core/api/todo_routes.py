"""Todo 日程路由。
提供日程数据的查询功能。
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from pydantic import BaseModel
from core.types.todo_data import ScheduleSave, ScheduleData

from core.config import app_logger
from core.services.todo_mgr import todo_mgr
from core.tools.validation import parse_with_model
from core.utils import _err, _ok, read_json_from_request

log = app_logger
todo_bp = Blueprint('todo', __name__)


@todo_bp.route('/todo/calendar', methods=['GET'])
def get_todo_calendar() -> ResponseReturnValue:
    """获取指定时间范围内的日历数据"""
    try:
        start_time = request.args.get('start_time', type=str) or request.args.get('startTime', type=str)
        end_time = request.args.get('end_time', type=str) or request.args.get('endTime', type=str)
        user_id = request.args.get('user_id', type=int) or request.args.get('userId', type=int)

        if not start_time or not end_time or user_id is None:
            return _err('start_time, end_time and user_id are required')

        result = todo_mgr.get_todo_calendar(
            start_time=start_time,
            end_time=end_time,
            user_id=user_id,
        )
        return result
    except Exception as e:
        log.error(f"[TodoRoutes] 获取日历数据异常: {e}", exc_info=True)
        return _err(f'error: {str(e)}')


@todo_bp.route('/todo/list', methods=['GET'])
def get_todo_list() -> ResponseReturnValue:
    """获取日程列表（分页）"""
    try:
        user_id = request.args.get('user_id', type=int)
        page_num = request.args.get('page_num', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        if user_id is None:
            return _err('user_id is required')

        result = todo_mgr.get_todo_list(
            user_id=user_id,
            page_num=page_num,
            page_size=page_size,
        )
        return result
    except Exception as e:
        log.error(f"[TodoRoutes] 获取日程列表异常: {e}", exc_info=True)
        return _err(f'error: {str(e)}')


@todo_bp.route('/todo/create', methods=['POST'])
def create_todo() -> ResponseReturnValue:
    """创建日程"""
    try:
        json_data = read_json_from_request()
        schedule_data = ScheduleData()
        schedule_data.title = json_data.get('title', '')
        schedule_data.startTs = json_data.get('startTs') or json_data.get('start_ts')
        schedule_data.endTs = json_data.get('endTs') or json_data.get('end_ts')
        schedule_data.allDay = json_data.get('allDay', 1)
        schedule_data.reminder = json_data.get('reminder', 0)
        schedule_data.repeat = json_data.get('repeat', 0)
        schedule_data.repeatData = json_data.get('repeatData') or json_data.get('repeat_data', {})
        schedule_data.repeatEndTs = json_data.get('repeatEndTs') or json_data.get('repeat_end_ts')
        schedule_data.color = json_data.get('color', 0)
        schedule_data.priority = json_data.get('priority', -1)
        # 处理 groupId，确保是 int 类型
        group_id_val = json_data.get('groupId')
        if group_id_val is None:
            group_id_val = json_data.get('group_id')
        if group_id_val is None:
            group_id_val = -1
        schedule_data.groupId = int(group_id_val) if group_id_val is not None else -1
        # 处理 order，确保是 int 类型
        order_val = json_data.get('order')
        if order_val is None:
            order_val = json_data.get('order_idx')
        if order_val is None:
            order_val = 0
        schedule_data.order = int(order_val) if order_val is not None else 0
        schedule_data.score = json_data.get('score')
        schedule_data.userId = json_data.get('userId') or json_data.get('user_id')

        # 解析子任务
        subtasks_raw = json_data.get('subtasks', [])
        if isinstance(subtasks_raw, list):
            from core.types.todo_data import Subtask
            schedule_data.subtasks = [Subtask.from_dict(st) for st in subtasks_raw]

        result = todo_mgr.create_todo(schedule_data)
        return result
    except Exception as e:
        log.error(f"[TodoRoutes] 创建日程异常: {e}", exc_info=True)
        return _err(f'error: {str(e)}')


@todo_bp.route('/todo/get', methods=['GET'])
def get_todo() -> ResponseReturnValue:
    """获取单个日程详情"""
    try:
        todo_id = request.args.get('id', type=int)
        date = request.args.get('date')
        user_id = request.args.get('user_id', type=int)

        if todo_id is None or not date or user_id is None:
            return _err('id, date and user_id are required')

        result = todo_mgr.get_todo(todo_id=todo_id, date=date, user_id=user_id)
        return result
    except Exception as e:
        log.error(f"[TodoRoutes] 获取日程详情异常: {e}", exc_info=True)
        return _err(f'error: {str(e)}')


@todo_bp.route('/todo/update', methods=['POST'])
def update_todo() -> ResponseReturnValue:
    """更新日程"""
    try:
        json_data = read_json_from_request()
        todo_id = json_data.get('id')
        if todo_id is None:
            return _err('id is required')

        schedule_data = ScheduleData()
        schedule_data.title = json_data.get('title', '')
        schedule_data.startTs = json_data.get('startTs') or json_data.get('start_ts')
        schedule_data.endTs = json_data.get('endTs') or json_data.get('end_ts')
        schedule_data.allDay = json_data.get('allDay', 1)
        schedule_data.reminder = json_data.get('reminder', 0)
        schedule_data.repeat = json_data.get('repeat', 0)
        schedule_data.repeatData = json_data.get('repeatData') or json_data.get('repeat_data', {})
        schedule_data.repeatEndTs = json_data.get('repeatEndTs') or json_data.get('repeat_end_ts')
        schedule_data.color = json_data.get('color', 0)
        schedule_data.priority = json_data.get('priority', -1)
        # 处理 groupId，确保是 int 类型
        group_id_val = json_data.get('groupId')
        if group_id_val is None:
            group_id_val = json_data.get('group_id')
        if group_id_val is None:
            group_id_val = -1
        schedule_data.groupId = int(group_id_val) if group_id_val is not None else -1
        # 处理 order，确保是 int 类型
        order_val = json_data.get('order')
        if order_val is None:
            order_val = json_data.get('order_idx')
        if order_val is None:
            order_val = 0
        schedule_data.order = int(order_val) if order_val is not None else 0
        schedule_data.score = json_data.get('score')
        schedule_data.userId = json_data.get('userId') or json_data.get('user_id')

        # 解析子任务
        subtasks_raw = json_data.get('subtasks', [])
        if isinstance(subtasks_raw, list):
            from core.types.todo_data import Subtask
            schedule_data.subtasks = [Subtask.from_dict(st) for st in subtasks_raw]

        result = todo_mgr.update_todo(todo_id=todo_id, schedule_data=schedule_data)
        return result
    except Exception as e:
        log.error(f"[TodoRoutes] 更新日程异常: {e}", exc_info=True)
        return _err(f'error: {str(e)}')


@todo_bp.route('/todo/delete', methods=['POST'])
def delete_todo() -> ResponseReturnValue:
    """删除日程"""
    try:
        json_data = read_json_from_request()
        todo_id = json_data.get('id')
        if todo_id is None:
            return _err('id is required')

        result = todo_mgr.delete_todo(todo_id=todo_id)
        return result
    except Exception as e:
        log.error(f"[TodoRoutes] 删除日程异常: {e}", exc_info=True)
        return _err(f'error: {str(e)}')


@todo_bp.route('/todo/save', methods=['POST'])
def save_todo() -> ResponseReturnValue:
    """保存日程在指定日期的完成状态"""
    try:
        json_data = read_json_from_request()
        schedule_id = json_data.get('schedule_id')
        date = json_data.get('date')
        if schedule_id is None or date is None:
            return _err('schedule_id or date are required')
        # 构建 ScheduleSave 对象
        schedule_save = ScheduleSave()
        schedule_save.scheduleId = schedule_id
        schedule_save.date = date
        schedule_save.state = json_data.get('state', 0)
        schedule_save.subtasks = json_data.get('subtasks', {})
        schedule_save.score = json_data.get('score')

        # 解析 schedule_override
        override_data = json_data.get('schedule_override')
        if override_data:
            schedule_save.scheduleOverride = ScheduleData()
            schedule_save.scheduleOverride.title = override_data.get('title', '')
            schedule_save.scheduleOverride.color = override_data.get('color', 0)
            schedule_save.scheduleOverride.priority = override_data.get('priority', -1)
            schedule_save.scheduleOverride.groupId = int(
                override_data.get('groupId')) if override_data.get('groupId') is not None else -1
            schedule_save.scheduleOverride.order = int(
                override_data.get('order')) if override_data.get('order') is not None else 0
            schedule_save.scheduleOverride.score = override_data.get('score')

        if schedule_save.scheduleId is None or not schedule_save.date:
            return _err('schedule_id and date are required')

        result = todo_mgr.save_todo(schedule_save)
        return result
    except Exception as e:
        log.error(f"[TodoRoutes] 保存日程状态异常: {e}", exc_info=True)
        return _err(f'error: {str(e)}')
