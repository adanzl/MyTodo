"""Todo 管理服务模块。
提供日程数据的查询功能，从 t_schedule 和 t_schedule_save 表中获取数据。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
from datetime import datetime, timedelta

from sqlalchemy import text

from core.config import app_logger
from core.db import db_obj
from core.db.db_mgr import db_mgr
from core.tools import serialize_data, serialize_object_list
from core.types.todo_data import ScheduleData, ScheduleSave, Subtask

log = app_logger


class TodoMgr:
    """Todo 管理类，封装日程数据的操作"""

    def _convert_schedules_to_list(self, schedules: List[dict]) -> List[dict]:
        """将数据库日程记录转换为 ScheduleData 列表"""
        return [ScheduleData.from_db_rows(schedule).to_dict() for schedule in schedules]

    def get_todo_list_by_time_range(self, start_time: str, end_time: str, user_id: int) -> Dict[str, Any]:
        """
        按时间范围获取日程列表

        Args:
            start_time: 开始时间（格式：YYYY-MM-DD）
            end_time: 结束时间（格式：YYYY-MM-DD）
            user_id: 用户ID

        Returns:
            日程列表数据
        """
        try:
            schedules_result = self._get_schedules_in_time_range(start_time, end_time, user_id)
            if schedules_result.get('code') != 0:
                return schedules_result

            schedule_list = self._convert_schedules_to_list(schedules_result['data'])

            return {
                "code": 0,
                "msg": "ok",
                "data": {
                    "data": schedule_list,
                    "totalCount": len(schedule_list),
                    "pageNum": 1,
                    "pageSize": len(schedule_list),
                    "totalPage": 1
                }
            }
        except Exception as e:
            log.error(f"[TodoMgr] 按时间范围获取日程列表异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}

    def get_todo_list(self, user_id: int, page_num: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        获取日程列表（分页）

        Args:
            user_id: 用户ID
            page_num: 页码，默认1
            page_size: 每页数量，默认20

        Returns:
            日程列表数据，包含分页信息
        """
        try:
            result = db_mgr.get_list(table='t_schedule',
                                     page_num=page_num,
                                     page_size=page_size,
                                     conditions={'user_id': user_id})

            if result.get('code') != 0:
                return result

            schedules = result['data'].get('data', []) if result.get('data') else []
            schedule_list = self._convert_schedules_to_list(schedules)

            return {
                "code": 0,
                "msg": "ok",
                "data": {
                    "data": schedule_list,
                    "totalCount": result['data'].get('totalCount', 0),
                    "pageNum": page_num,
                    "pageSize": page_size,
                    "totalPage": result['data'].get('totalPage', 0)
                }
            }
        except Exception as e:
            log.error(f"[TodoMgr] 获取日程列表异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}

    def _get_schedules_in_time_range(self, start_time: str, end_time: str, user_id: int) -> Dict[str, Any]:
        """
        获取用户在指定时间范围内的日程模板。

        Args:
            start_time: 开始时间（格式：YYYY-MM-DD）
            end_time: 结束时间（格式：YYYY-MM-DD）
            user_id: 用户ID

        Returns:
            包含日程列表的字典，格式为 {"code": 0, "msg": "ok", "data": [schedules]}
        """
        try:
            # 获取用户的可能在时间范围内显示的日程模板
            # end_time 补上时间后缀，确保 start_ts <= end_time 的字符串比较不会因为
            # start_ts 带时间而漏掉当天数据（如 '2026-07-05T00:00:00+08:00' <= '2026-07-05T23:59:59'）
            end_ts_bound = end_time + 'T23:59:59'
            schedules_sql = f"""
                SELECT * FROM t_schedule 
                WHERE user_id = {user_id}
                  AND start_ts <= '{end_ts_bound}'
                  AND (
                    (repeat != 0 AND (repeat_end_ts IS NULL OR repeat_end_ts >= '{start_time}'))
                    OR (repeat = 0 AND (end_ts IS NULL OR end_ts >= '{start_time}'))
                  )
            """
            schedules_result = db_mgr.query(schedules_sql)

            if schedules_result.get('code') != 0:
                return schedules_result

            return {"code": 0, "msg": "ok", "data": schedules_result['data']}
        except Exception as e:
            log.error(f"[TodoMgr] 获取时间范围内日程异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}

    def get_todo_calendar(self, start_time: str, end_time: str, user_id: int) -> Dict[str, Any]:
        """获取指定时间范围内的日历数据，返回每天的 ScheduleData 列表。"""
        try:
            # 1. 获取时间范围内的日程模板
            schedules_result = self._get_schedules_in_time_range(start_time, end_time, user_id)
            if schedules_result.get('code') != 0:
                return schedules_result

            schedules = schedules_result['data']

            # 2. 获取时间范围内的存档数据
            saves_sql = f"SELECT * FROM t_schedule_save WHERE date >= '{start_time}' AND date <= '{end_time}'"
            saves_result = db_mgr.query(saves_sql)
            if saves_result.get('code') != 0:
                return saves_result

            saves = saves_result['data']

            # 3. 按日期组织数据
            result = {}
            start_dt = datetime.strptime(start_time, '%Y-%m-%d')
            end_dt = datetime.strptime(end_time, '%Y-%m-%d')
            current_dt = start_dt

            while current_dt <= end_dt:
                date_str = current_dt.strftime('%Y-%m-%d')
                result[date_str] = []

                # 为每个日程模板判断是否在该日期显示
                for schedule in schedules:
                    if not self._should_show_on_date(schedule, current_dt):
                        continue

                    # 查找该日期的存档
                    save = next((s for s in saves if s['schedule_id'] == schedule['id'] and s['date'] == date_str),
                                None)

                    # 创建 ScheduleData（会自动应用覆盖数据）
                    schedule_data = ScheduleData.from_db_rows(schedule, save)
                    result[date_str].append(schedule_data.to_dict())

                current_dt += timedelta(days=1)

            return {"code": 0, "msg": "ok", "data": result}
        except Exception as e:
            log.error(f"[TodoMgr] 获取日历数据异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}

    def _should_show_on_date(self, schedule: dict, target_dt: datetime) -> bool:
        """判断日程是否在指定日期显示（按照前端逻辑）"""
        try:
            start_ts = schedule.get('start_ts')
            if not start_ts:
                return False

            start_dt = datetime.fromisoformat(start_ts.replace('Z', '+00:00'))
            start_day = start_dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

            target_day = target_dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

            if start_day > target_day:
                return False

            if start_day == target_day:
                return True

            repeat_end_ts = schedule.get('repeat_end_ts')
            if repeat_end_ts:
                repeat_end_dt = datetime.fromisoformat(repeat_end_ts.replace('Z', '+00:00'))
                if repeat_end_dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None) < target_day:
                    return False

            repeat = schedule.get('repeat', 0)

            if repeat == 1:  # daily
                return True
            elif repeat == 2:  # weekly
                return target_dt.isoweekday() % 7 == start_dt.isoweekday() % 7
            elif repeat == 3:  # monthly
                return target_dt.day == start_dt.day
            elif repeat == 4:  # annually
                return target_dt.day == start_dt.day and target_dt.month == start_dt.month
            elif repeat == 5:  # workday
                return target_dt.isoweekday() < 6
            elif repeat == 6:  # weekend
                return target_dt.isoweekday() >= 6
            elif repeat == 999:  # custom
                repeat_data = json.loads(schedule['repeat_data']) if schedule.get('repeat_data') else {}
                return (target_dt.isoweekday() % 7) in repeat_data.get('week', [])
            else:
                return False
        except Exception as e:
            log.error(f"[TodoMgr] 判断日程显示异常: {e}", exc_info=True)
            return False

    def create_todo(self, schedule_data: ScheduleData) -> Dict[str, Any]:
        """
        创建日程。

        Args:
            schedule_data: 日程数据对象

        Returns:
            操作结果
        """
        try:
            # 将 ScheduleData 转换为数据库字段
            db_data = {
                'title': schedule_data.title,
                'start_ts': schedule_data.startTs,
                'end_ts': schedule_data.endTs,
                'all_day': schedule_data.allDay,
                'reminder': schedule_data.reminder,
                'repeat': schedule_data.repeat,
                'repeat_data': serialize_data(schedule_data.repeatData),
                'repeat_end_ts': schedule_data.repeatEndTs,
                'color': schedule_data.color,
                'priority': schedule_data.priority,
                'group_id': schedule_data.groupId,
                'order_idx': schedule_data.order,
                'score': schedule_data.score,
                'subtasks': serialize_object_list(schedule_data.subtasks),
                'user_id': schedule_data.userId
            }

            result = db_mgr.set_data('t_schedule', db_data)
            if result.get('code') == 0:
                log.info(f"[TodoMgr] 创建日程成功: id={result.get('data')}")
            else:
                log.error(f"[TodoMgr] 创建日程失败: {result.get('msg')}")
            return result
        except Exception as e:
            log.error(f"[TodoMgr] 创建日程异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}

    def get_todo(self, todo_id: int, date: str, user_id: int) -> Dict[str, Any]:
        """
        获取单个日程在指定日期的详情（含完成状态和覆盖数据）。

        Args:
            todo_id: 日程ID
            date: 日期（格式：YYYY-MM-DD）
            user_id: 用户ID

        Returns:
            日程详情数据
        """
        try:
            # 1. 从 t_schedule 表获取日程模板
            result = db_mgr.get_data('t_schedule', todo_id, '*')
            if result.get('code') != 0:
                return result

            row = result.get('data')
            if not row:
                return {"code": -1, "msg": "日程不存在或无权限"}

            # 2. 从 t_schedule_save 表获取该日期的存档数据
            save_sql = f"SELECT * FROM t_schedule_save WHERE schedule_id = {todo_id} AND date = '{date}'"
            save_result = db_mgr.query(save_sql)

            # 3. 合并数据创建 ScheduleData
            save_row_dict = None
            if save_result.get('code') == 0 and save_result.get('data'):
                save_row_dict = save_result['data'][0]

            schedule = ScheduleData.from_db_rows(row, save_row_dict)

            log.info(f"[TodoMgr] 获取日程详情成功: todo_id={todo_id}, date={date}, user_id={user_id}")
            return {"code": 0, "msg": "ok", "data": schedule.to_dict()}

        except Exception as e:
            log.error(f"[TodoMgr] 获取日程详情异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}

    def update_todo(self, todo_id: int, schedule_data: ScheduleData) -> Dict[str, Any]:
        """
        更新日程模板，不处理存档
        Args:
            todo_id: 日程ID
            schedule_data: 日程数据对象

        Returns:
            操作结果
        """
        try:
            db_data = {
                'id': todo_id,
                'title': schedule_data.title,
                'start_ts': schedule_data.startTs,
                'end_ts': schedule_data.endTs,
                'all_day': schedule_data.allDay,
                'reminder': schedule_data.reminder,
                'repeat': schedule_data.repeat,
                'repeat_data': serialize_data(schedule_data.repeatData),
                'repeat_end_ts': schedule_data.repeatEndTs,
                'color': schedule_data.color,
                'priority': schedule_data.priority,
                'group_id': schedule_data.groupId,
                'order_idx': schedule_data.order,
                'score': schedule_data.score,
                'subtasks': serialize_object_list(schedule_data.subtasks),
                'user_id': schedule_data.userId
            }

            result = db_mgr.set_data('t_schedule', db_data)
            if result.get('code') == 0:
                log.info(f"[TodoMgr] 更新日程成功: id={todo_id}")
            else:
                log.error(f"[TodoMgr] 更新日程失败: {result.get('msg')}")
            return result
        except Exception as e:
            log.error(f"[TodoMgr] 更新日程异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}

    def delete_todo(self, todo_id: int) -> Dict[str, Any]:
        """
        删除日程。

        Args:
            todo_id: 日程ID

        Returns:
            操作结果
        """
        try:
            # 1. 先删除 t_schedule_save 中相关的保存数据
            delete_save_sql = """
                DELETE FROM t_schedule_save 
                WHERE schedule_id = :schedule_id
            """
            db_obj.session.execute(text(delete_save_sql), {'schedule_id': todo_id})

            # 2. 再删除 t_schedule 中的日程数据
            result = db_mgr.del_data('t_schedule', todo_id)

            if result.get('code') == 0:
                db_obj.session.commit()
                log.info(f"[TodoMgr] 删除日程成功: id={todo_id}")
            else:
                db_obj.session.rollback()
                log.error(f"[TodoMgr] 删除日程失败: {result.get('msg')}")
            return result
        except Exception as e:
            db_obj.session.rollback()
            log.error(f"[TodoMgr] 删除日程异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}

    def save_todo(self, schedule_save: ScheduleSave) -> Dict[str, Any]:
        """保存日程在指定日期的完成状态。"""
        try:
            # 1. 查询是否存在该 schedule_id 和 date 组合的记录
            query_sql = f"""
                SELECT id, state, score FROM t_schedule_save 
                WHERE schedule_id = {schedule_save.scheduleId} AND date = '{schedule_save.date}'
            """
            query_result = db_mgr.query(query_sql)

            old_state = 0
            old_score = 0
            existing_record = None

            if query_result.get('code') == 0 and query_result.get('data'):
                existing_record = query_result['data'][0]
                old_state = existing_record.get('state', 0)
                old_score = existing_record.get('score', 0) or 0

            # 2. 准备保存数据
            db_data = {
                'schedule_id':
                schedule_save.scheduleId,
                'date':
                schedule_save.date,
                'state':
                schedule_save.state,
                'subtasks':
                serialize_data(schedule_save.subtasks),
                'schedule_override':
                serialize_data(schedule_save.scheduleOverride.to_dict() if schedule_save.scheduleOverride else None),
            }

            # 如果存在记录，添加 id 用于更新
            if existing_record:
                db_data['id'] = existing_record['id']

            # 3. 保存或更新记录
            result = db_mgr.set_data('t_schedule_save', db_data)
            save_id = result.get('data') if result.get('code') == 0 else None

            # 4. 如果状态改变，更新用户总积分
            if old_state != schedule_save.state and result.get('code') == 0:
                self._update_user_score(schedule_save.scheduleId, old_state, schedule_save.state, old_score, save_id)

            log.info(f"[TodoMgr] 保存日程状态{'成功' if result.get('code') == 0 else '失败'}: "
                     f"schedule_id={schedule_save.scheduleId}, date={schedule_save.date}, state={schedule_save.state}")
            return result
        except Exception as e:
            log.error(f"[TodoMgr] 保存日程状态异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}

    def _update_user_score(self, schedule_id: int, old_state: int, new_state: int, old_score: int,
                           save_id: Optional[int]) -> None:
        """
        根据日程状态变化更新用户积分

        Args:
            schedule_id: 日程ID
            old_state: 旧状态
            new_state: 新状态
            old_score: 旧积分
            save_id: 保存记录ID
        """
        try:
            # 获取日程所属用户ID和模板积分
            schedule_query = db_mgr.query(f"SELECT user_id, score FROM t_schedule WHERE id = {schedule_id}")

            if not (schedule_query.get('code') == 0 and schedule_query.get('data')):
                return

            user_id = schedule_query['data'][0]['user_id']
            template_score = schedule_query['data'][0].get('score', 0) or 0

            # 获取用户当前积分
            user_query = db_mgr.query(f"SELECT score FROM t_user WHERE id = {user_id}")

            if not (user_query.get('code') == 0 and user_query.get('data')):
                return

            current_score = user_query['data'][0].get('score', 0) or 0
            new_score = current_score

            # 从未完成变为完成：加积分
            if old_state == 0 and new_state == 1:
                if template_score > 0:
                    new_score = current_score + template_score
                    log.info(f"[TodoMgr] 用户 {user_id} 获得 {template_score} 积分，当前总分: {new_score}")
                    if save_id is not None:
                        db_mgr.set_data('t_schedule_save', {'id': save_id, 'score': template_score})
            # 从完成变为未完成：扣积分
            else:
                if old_score > 0:
                    new_score = max(0, current_score - old_score)
                    log.info(f"[TodoMgr] 用户 {user_id} 扣除 {old_score} 积分，当前总分: {new_score}")
                    if save_id is not None:
                        db_mgr.set_data('t_schedule_save', {'id': save_id, 'score': 0})

            # 更新用户积分
            if new_score != current_score:
                db_mgr.set_data('t_user', {'id': user_id, 'score': new_score})
        except Exception as e:
            log.error(f"[TodoMgr] 更新用户积分异常: {e}", exc_info=True)


todo_mgr = TodoMgr()
