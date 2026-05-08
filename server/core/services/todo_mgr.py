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
from core.types.todo_data import ScheduleData, ScheduleSave, Subtask

log = app_logger


class TodoMgr:
    """Todo 管理类，封装日程数据的操作"""

    def get_todo_calendar(self, start_time: str, end_time: str, user_id: int) -> Dict[str, Any]:
        """获取指定时间范围内的日历数据，返回每天的 ScheduleData 列表。"""
        try:
            # 1. 获取用户的可能在时间范围内显示的日程模板
            # 条件：已开始(start_ts <= end_time) 且
            #   - repeat=1(每天): repeat_end_ts IS NULL OR repeat_end_ts >= start_time
            #   - repeat!=1: end_ts IS NULL OR end_ts >= start_time
            schedules_sql = f"""
                SELECT * FROM t_schedule 
                WHERE user_id = {user_id} 
                  AND start_ts <= '{end_time}'
                  AND (
                    (repeat != 0 AND (repeat_end_ts IS NULL OR repeat_end_ts >= '{start_time}'))
                    OR (repeat == 0 AND (end_ts IS NULL OR end_ts >= '{start_time}'))
                  )
            """
            schedules_result = db_mgr.query(schedules_sql)
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
                    save = next((s for s in saves if s['schedule_id'] == schedule['id'] and s['date'] == date_str), None)

                    # 创建 ScheduleData（会自动应用覆盖数据）
                    schedule_data = ScheduleData.from_db_rows(schedule, save)
                    result[date_str].append(schedule_data.to_dict())

                current_dt += timedelta(days=1)

            log.info(f"[TodoMgr] 获取日历数据成功: user_id={user_id}, dates={len(result)}")
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

            # 统一转换为 naive datetime
            log.info(f"[TodoMgr] start_ts raw: {start_ts}, type: {type(start_ts)}")
            start_dt = datetime.fromisoformat(start_ts.replace('Z', '+00:00'))
            log.info(f"[TodoMgr] start_dt: {start_dt}, tzinfo: {start_dt.tzinfo}")
            if start_dt.tzinfo is not None:
                start_dt = start_dt.replace(tzinfo=None)
            start_day = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            
            log.info(f"[TodoMgr] target_dt: {target_dt}, tzinfo: {target_dt.tzinfo}")
            target_day = target_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            if target_day.tzinfo is not None:
                target_day = target_day.replace(tzinfo=None)
            
            log.info(f"[TodoMgr] start_day: {start_day}, target_day: {target_day}")

            if start_day > target_day:
                return False

            if start_day == target_day:
                return True

            repeat_end_ts = schedule.get('repeat_end_ts')
            if repeat_end_ts:
                repeat_end_dt = datetime.fromisoformat(repeat_end_ts.replace('Z', '+00:00')).replace(tzinfo=None)
                if repeat_end_dt < target_day:
                    return False

            repeat = schedule.get('repeat', 0)

            if repeat == 1: # daily
                return True
            elif repeat == 2: # weekly
                return target_dt.isoweekday() % 7 == start_dt.isoweekday() % 7
            elif repeat == 3: # monthly
                return target_dt.day == start_dt.day
            elif repeat == 4: # annually
                return target_dt.day == start_dt.day and target_dt.month == start_dt.month
            elif repeat == 5: # workday
                return target_dt.isoweekday() < 6
            elif repeat == 6: # weekend
                return target_dt.isoweekday() >= 6
            elif repeat == 999:  # custom
                repeat_data = json.loads(schedule['repeat_data']) if schedule.get('repeat_data') else {}
                return (target_dt.isoweekday() % 7) in repeat_data.get('week', [])
            else:
                return False
        except Exception as e:
            log.error(f"[TodoMgr] 判断日程显示异常: {e}", exc_info=True)
            return False

    def create_todo(
        self,
        schedule_data: ScheduleData,
    ) -> Dict[str, Any]:
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
                'title':
                schedule_data.title,
                'start_ts':
                schedule_data.startTs,
                'end_ts':
                schedule_data.endTs,
                'all_day':
                schedule_data.allDay,
                'reminder':
                schedule_data.reminder,
                'repeat_type':
                schedule_data.repeat,
                'repeat_data':
                json.dumps(schedule_data.repeatData, ensure_ascii=False) if schedule_data.repeatData else None,
                'repeat_end_ts':
                schedule_data.repeatEndTs,
                'color':
                schedule_data.color,
                'priority':
                schedule_data.priority,
                'group_id':
                schedule_data.groupId,
                'order_num':
                schedule_data.order,
                'score':
                schedule_data.score,
                'subtasks':
                json.dumps([st.__dict__
                            for st in schedule_data.subtasks], ensure_ascii=False) if schedule_data.subtasks else None,
                'user_id':
                schedule_data.userId
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

    def get_todo(
        self,
        todo_id: int,
        date: str,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        获取单个日程在指定日期的详情（含完成状态和覆盖数据）。
        模拟前端 createDayData 的逻辑，根据重复规则判断日程是否在指定日期显示，
        并合并该日期的存档数据（state、subtask_states、override_data）。

        Args:
            todo_id: 日程ID
            date: 日期（格式：YYYY-MM-DD）
            user_id: 用户ID

        Returns:
            日程详情数据， ScheduleData 
        """
        try:
            # 1. 从 t_schedule 表获取日程模板
            result = db_mgr.get_data('t_schedule', todo_id, '*')
            if result.get('code') != 0:
                return result

            row = result.get('data')
            if not row:
                return {"code": -1, "msg": "日程不存在或无权限"}

            # 从 t_schedule_save 表获取该日期的存档数据
            save_sql = f"""
                SELECT *
                FROM t_schedule_save 
                WHERE schedule_id = {todo_id} AND date = '{date}'
            """
            save_result = db_mgr.query(save_sql)

            # 合并数据创建 ScheduleData
            save_row_dict = None
            if save_result.get('code') == 0 and save_result.get('data'):
                save_row_dict = save_result['data'][0]

            schedule = ScheduleData.from_db_rows(row, save_row_dict)

            log.info(f"[TodoMgr] 获取日程详情成功: todo_id={todo_id}, date={date}, user_id={user_id}")
            return {"code": 0, "msg": "ok", "data": schedule.to_dict()}

        except Exception as e:
            log.error(f"[TodoMgr] 获取日程详情异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}

    def update_todo(
        self,
        todo_id: int,
        schedule_data: ScheduleData,
    ) -> Dict[str, Any]:
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
                'repeat_data': json.dumps(schedule_data.repeatData, ensure_ascii=False) if schedule_data.repeatData else None,
                'repeat_end_ts': schedule_data.repeatEndTs,
                'color': schedule_data.color,
                'priority': schedule_data.priority,
                'group_id': schedule_data.groupId,
                'order_idx': schedule_data.order,
                'score': schedule_data.score,
                'subtasks': json.dumps([st.__dict__ for st in schedule_data.subtasks], ensure_ascii=False) if schedule_data.subtasks else None,
                'user_id': schedule_data.userId,
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

    def delete_todo(
        self,
        todo_id: int,
    ) -> Dict[str, Any]:
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
            db_data = {
                'schedule_id': schedule_save.scheduleId,
                'date': schedule_save.date,
                'state': schedule_save.state,
                'subtasks': json.dumps(schedule_save.subtasks, ensure_ascii=False) if schedule_save.subtasks else None,
                'score': schedule_save.score,
                'schedule_override': json.dumps(schedule_save.scheduleOverride.to_dict(), ensure_ascii=False) if schedule_save.scheduleOverride else None,
            }
            result = db_mgr.set_data('t_schedule_save', db_data)
            log.info(f"[TodoMgr] 保存日程状态{'成功' if result.get('code') == 0 else '失败'}: schedule_id={schedule_save.scheduleId}, date={schedule_save.date}")
            return result
        except Exception as e:
            log.error(f"[TodoMgr] 保存日程状态异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}


todo_mgr = TodoMgr()
