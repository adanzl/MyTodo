"""
素材管理服务
提供素材的增删改查功能
"""
from typing import Any, Dict, List, Optional, Tuple
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

            conditions: Dict[str, Any] = {}
            if user_id and user_id > 0:
                conditions['user_id'] = {'like': f'%{user_id}%'}

            result = db_mgr.get_list(TABLE_TASK, page_num=1, page_size=1000, conditions=conditions)

            if result.get('code') != 0:
                log.error(f"获取任务列表失败: {result.get('msg')}")
                return {"code": -1, "msg": "获取任务列表失败", "data": None}

            tasks = result.get('data', {}).get('data', [])

            calendar_data: Dict[str, Dict[str, Any]] = {}

            for day in range(1, days_in_month + 1):
                current_date = datetime(year, month, day)
                date_key = current_date.strftime('%Y-%m-%d')

                calendar_data[date_key] = {'date': date_key, 'tasks': []}

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

                        materials_for_day = daily_materials.get(str(day_offset), [])

                        total_count = len(materials_for_day)
                        completed_count = sum(1 for m in materials_for_day if m.get('status') == 1)

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
                    'calendar': calendar_data
                }
            }

        except Exception as e:
            log.error(f"获取任务日历失败: {e}")
            return {"code": -1, "msg": f"获取任务日历失败: {str(e)}", "data": None}


task_mgr = TaskMgr()
