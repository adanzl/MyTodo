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
            log.info(f"查询到 {len(tasks)} 个任务")

            calendar_data: Dict[str, Dict[str, Any]] = {}

            for task in tasks:
                try:
                    task_id = task.get('id')
                    task_name = task.get('name', '')
                    start_date_str = task.get('start_date', '')
                    duration = task.get('duration', 0)
                    task_data_str = task.get('data', '{}')
                    task_type = task.get('type', 0)

                    log.info(
                        f"处理任务: id={task_id}, name={task_name}, type={task_type}, start={start_date_str}, duration={duration}"
                    )

                    if not start_date_str or duration <= 0:
                        continue

                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                    end_date = start_date + timedelta(days=duration - 1)

                    task_data = json.loads(task_data_str) if isinstance(task_data_str, str) else task_data_str
                    daily_materials = task_data.get('dailyMaterials', {})
                    task_type = task.get('type', 0)  # 获取任务类型

                    for day_offset in range(duration):
                        current_date = start_date + timedelta(days=day_offset)

                        if current_date.month != month or current_date.year != year:
                            continue

                        date_key = current_date.strftime('%Y-%m-%d')

                        if date_key not in calendar_data:
                            calendar_data[date_key] = {'date': date_key, 'tasks': []}

                        # type=1（持续任务）：所有素材都在第0天
                        materials_index = 0 if task_type == 1 else day_offset
                        materials_for_day = daily_materials.get(str(materials_index), [])

                        total_count = len(materials_for_day)
                        # status 现在是 Record<user_id, status>，根据 user_id 统计完成情况
                        if user_id and user_id > 0:
                            # 特定用户：只统计该用户的完成状态
                            def check_user_completed(m):
                                status = m.get('status')
                                if not status:
                                    return False
                                # 兼容旧格式：status 是整数，直接返回 false
                                if isinstance(status, int):
                                    return False
                                # 新格式：status 是 Record
                                return status.get(str(user_id)) == 1

                            completed_count = sum(1 for m in materials_for_day if check_user_completed(m))
                        else:
                            # 全部用户：素材有任何一个用户完成就算完成
                            def any_user_completed(m):
                                status = m.get('status')
                                if not status:
                                    return False
                                # 兼容旧格式：status 是整数，直接返回 false
                                if isinstance(status, int):
                                    return False
                                # 新格式：检查是否有任何用户的状态是 1
                                return any(v == 1 for v in status.values())

                            completed_count = sum(1 for m in materials_for_day if any_user_completed(m))

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

    def finish_material(self, task_id: int, material_id: int, date_str: str, user_id: int) -> Dict[str, Any]:
        """
        完成素材打卡
        
        Args:
            task_id: 任务ID
            material_id: 素材ID
            date_str: 日期字符串，格式 YYYY-MM-DD
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        try:
            # 获取任务信息
            task_result = db_mgr.get_data(TABLE_TASK, task_id, '*')
            if task_result.get('code') != 0 or not task_result.get('data'):
                return {"code": -1, "msg": "任务不存在", "data": None}

            task = task_result['data']

            # 解析任务数据
            task_data_str = task.get('data', '{}')
            task_data = json.loads(task_data_str) if isinstance(task_data_str, str) else task_data_str
            daily_materials = task_data.get('dailyMaterials', {})

            # 计算天数索引
            start_date_str = task.get('start_date', '')
            if not start_date_str:
                return {"code": -1, "msg": "任务开始日期不存在", "data": None}

            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            day_offset = (target_date - start_date).days

            if day_offset < 0 or day_offset >= task.get('duration', 0):
                return {"code": -1, "msg": "日期不在任务范围内", "data": None}

            # type=1（持续任务）：所有素材都在第0天
            materials_index = 0 if task.get('type', 0) == 1 else day_offset
            materials_for_day = daily_materials.get(str(materials_index), [])

            # 查找目标素材并更新状态
            found = False
            for material in materials_for_day:
                if material.get('id') == material_id:
                    # 初始化 status 字段
                    if 'status' not in material:
                        material['status'] = {}
                    # 设置用户完成状态
                    material['status'][str(user_id)] = 1
                    found = True
                    break

            if not found:
                return {"code": -1, "msg": "素材不存在于该天", "data": None}

            # 保存更新后的任务数据
            task_data['dailyMaterials'] = daily_materials
            updated_data = json.dumps(task_data, ensure_ascii=False)

            update_result = db_mgr.set_data(TABLE_TASK, {'id': task_id, 'data': updated_data})
            if update_result.get('code') != 0:
                return {"code": -1, "msg": "更新失败", "data": None}

            # 检查是否完成当天所有素材，如果完成则加分
            all_completed = all(m.get('status', {}).get(str(user_id)) == 1 for m in materials_for_day)

            score_added = 0
            if all_completed:
                # 获取当日分数
                score = task_data.get('dailyScore', {}).get(str(materials_index), 0)

                if score > 0:
                    # 添加积分
                    add_score_result = db_mgr.add_score(user_id=user_id,
                                                        value=score,
                                                        action='task',
                                                        msg=f'完成任务: {task.get("name", "")} 第{materials_index + 1}天')

                    if add_score_result.get('code') != 0:
                        log.error(f"添加积分失败: {add_score_result.get('msg')}")
                    else:
                        score_added = score

            return {"code": 0, "msg": "ok", "data": {"success": True, "score": score_added}}

        except Exception as e:
            log.error(f"完成素材打卡失败: {e}")
            return {"code": -1, "msg": f"完成素材打卡失败: {str(e)}", "data": None}


task_mgr = TaskMgr()
