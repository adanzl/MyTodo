"""
素材管理服务
提供素材的增删改查功能
"""
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import calendar as calendar_module
import json

from core.config import app_logger
from core.db.db_mgr import db_mgr

log = app_logger

TABLE_MATERIAL = 't_material'
TABLE_TASK = 't_task'


class TaskMgr:
    """任务管理器 - 素材管理"""

    def __init__(self) -> None:
        """初始化管理器"""
        pass

    def get_task_calendar(self, date_str: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取任务日历数据
        
        Args:
            date_str: 日期字符串，格式 YYYY-MM-DD
            user_id: 用户ID（可选）
            
        Returns:
            包含当月每天任务完成情况的字典
        """
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            year = target_date.year
            month = target_date.month

            days_in_month = calendar_module.monthrange(year, month)[1]
            month_start = datetime(year, month, 1)
            month_end = datetime(year, month, days_in_month, 23, 59, 59)

            conditions: Dict[str, Any] = {
                'start_date': {
                    '<=': month_end.strftime('%Y-%m-%d')
                },
                'end_date': {
                    '>=': month_start.strftime('%Y-%m-%d')
                }
            }
            if user_id and user_id > 0:
                conditions['user_id'] = {'like': f'%{user_id}%'}

            result = db_mgr.get_list(TABLE_TASK, page_num=1, page_size=1000, conditions=conditions)

            if result.get('code') != 0:
                log.error(f"获取任务列表失败: {result.get('msg')}")
                return {"code": -1, "msg": "获取任务列表失败", "data": None}

            tasks = result.get('data', {}).get('data', [])

            calendar_data: Dict[str, Dict[str, Any]] = {}

            for task in tasks:
                try:
                    task_id = task.get('id')
                    task_name = task.get('name', '')
                    start_date_str = task.get('start_date', '')
                    duration = task.get('duration', 0)
                    task_data_str = task.get('data', '{}')

                    if not start_date_str or duration <= 0:
                        continue

                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                    end_date = start_date + timedelta(days=duration - 1)

                    task_data = json.loads(task_data_str) if isinstance(task_data_str, str) else task_data_str
                    daily_materials = task_data.get('dailyMaterials', {})

                    for day_offset in range(duration):
                        current_date = start_date + timedelta(days=day_offset)

                        if current_date.month != month or current_date.year != year:
                            continue

                        date_key = current_date.strftime('%Y-%m-%d')

                        if date_key not in calendar_data:
                            calendar_data[date_key] = {'date': date_key, 'tasks': []}

                        materials_for_day = daily_materials.get(str(day_offset), [])

                        total_count = len(materials_for_day)
                        # status 现在是 Record<user_id, status>，根据 user_id 统计完成情况
                        if user_id and user_id > 0:
                            # 特定用户：只统计该用户的完成状态
                            completed_count = sum(1 for m in materials_for_day
                                                  if m.get('status') and m.get('status', {}).get(str(user_id)) == 1)
                        else:
                            # 全部用户：需要所有用户都完成才算完成
                            def all_users_completed(m):
                                if not m.get('status'):
                                    return False
                                # 检查是否所有用户的状态都是 1
                                return all(v == 1 for v in m.get('status', {}).values())

                            completed_count = sum(1 for m in materials_for_day if all_users_completed(m))

                        calendar_data[date_key]['tasks'].append({
                            'task_id': task_id,
                            'task_name': task_name,
                            'total': total_count,
                            'completed': completed_count,
                            'materials': materials_for_day
                        })

                except Exception as e:
                    log.error(f"处理任务 {task.get('id')} 时出错: {e}")
                    continue

            calendar_list = list(calendar_data.values())
            calendar_list.sort(key=lambda x: x['date'])

            return {
                "code": 0,
                "msg": "ok",
                "data": {
                    'year': year,
                    'month': month,
                    'days_in_month': days_in_month,
                    'calendar': {
                        item['date']: item
                        for item in calendar_list
                    }
                }
            }

        except Exception as e:
            log.error(f"获取任务日历失败: {e}")
            return {"code": -1, "msg": f"获取任务日历失败: {str(e)}", "data": None}


task_mgr = TaskMgr()
