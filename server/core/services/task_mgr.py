"""
素材管理服务
提供素材的增删改查功能
"""
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
import calendar as calendar_module
import json
import os
from pathlib import Path

from core.config import app_logger
from core.db.db_mgr import db_mgr

log = app_logger

TABLE_MATERIAL = 't_material'
TABLE_TASK = 't_task'
TABLE_MATERIAL_CATEGORY = 't_material_category'


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

            # 检查任务锁定状态
            if user_id and user_id > 0:
                tasks = self.check_task_lock(tasks, user_id, date_str)

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

                    # 获取前置日程数据（JSON格式：{"user_id": [todo_ids]}）
                    pre_todo = json.loads(task.get('pre_todo', '{}'))

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
                            'materials': materials_for_day,
                            'pre_todo': pre_todo,
                            'lock': task.get('lock', False),
                            'msg': task.get('msg', '')
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

    def delete_material_category(self, category_id: int, delete_materials: bool = False) -> Dict[str, Any]:
        """
        删除素材分类（文件夹）
        
        Args:
            category_id: 分类ID
            delete_materials: 是否删除类别下的素材，默认False
            
        Returns:
            操作结果
        """
        try:
            # 递归获取所有子类别ID
            def get_all_children_ids(parent_id: int) -> List[int]:
                children_ids = []
                result = db_mgr.get_list(TABLE_MATERIAL_CATEGORY,
                                         page_num=1,
                                         page_size=1000,
                                         conditions={'parent': parent_id})
                if result.get('code') == 0:
                    children = result.get('data', {}).get('data', [])
                    for child in children:
                        child_id = child.get('id')
                        if child_id is not None:
                            children_ids.append(child_id)
                            # 递归获取子类别的子类别
                            children_ids.extend(get_all_children_ids(child_id))
                return children_ids

            all_category_ids = [category_id] + get_all_children_ids(category_id)
            log.info(f'待删除的分类IDs: {all_category_ids}')

            # 如果不删除素材，检查是否有素材
            if not delete_materials:
                for cat_id in all_category_ids:
                    materials_result = db_mgr.get_list(TABLE_MATERIAL,
                                                       page_num=1,
                                                       page_size=1,
                                                       conditions={'cate_id': cat_id})
                    if materials_result.get('code') == 0 and materials_result.get('data', {}).get('total', 0) > 0:
                        return {"code": -1, "msg": f"该目录或其子目录下还有素材，无法删除（可勾选'同时删除素材'）", "data": None}

            # 如果删除素材，先删除所有类别下的素材
            if delete_materials:
                for cat_id in all_category_ids:
                    materials_result = db_mgr.get_list(TABLE_MATERIAL,
                                                       page_num=1,
                                                       page_size=1000,
                                                       conditions={'cate_id': cat_id})
                    if materials_result.get('code') == 0:
                        materials = materials_result.get('data', {}).get('data', [])
                        for material in materials:
                            material_id = material.get('id')
                            if material_id is not None:
                                db_mgr.del_data(TABLE_MATERIAL, material_id)
                                log.info(f'删除素材: id={material_id}')

            # 从叶子节点开始删除类别（避免外键约束问题）
            all_category_ids.reverse()
            for cat_id in all_category_ids:
                result = db_mgr.del_data(TABLE_MATERIAL_CATEGORY, cat_id)
                if result.get('code') != 0:
                    log.error(f'删除分类失败: id={cat_id}, msg={result.get("msg")}')
                    return {"code": -1, "msg": f"删除分类 {cat_id} 失败: {result.get('msg')}", "data": None}
                log.info(f'删除分类成功: id={cat_id}')

            return {"code": 0, "msg": "删除成功", "data": None}
        except Exception as e:
            log.error(f'删除素材分类失败: {e}')
            return {"code": -1, "msg": f"删除失败: {str(e)}", "data": None}

    def get_task_list(self, user_id: Optional[int] = None, date: Optional[str] = None, 
                      page_num: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        获取任务列表
        
        Args:
            user_id: 用户ID
            date: 日期字符串，格式 YYYY-MM-DD
            page_num: 页码
            page_size: 每页数量
            
        Returns:
            任务列表响应数据
        """
        try:
            # 构建查询条件
            conditions: Dict[str, Any] = {}
            
            if user_id and user_id > 0:
                conditions['user_id'] = {'like': f'%{user_id}%'}
            
            if date:
                conditions['start_date'] = {'<=': date}
                conditions['end_date'] = {'>=': date}
            
            # 获取任务列表
            result = db_mgr.get_list(TABLE_TASK, page_num=page_num, page_size=page_size, conditions=conditions)
            
            if result.get('code') != 0:
                return result
            
            tasks = result.get('data', {}).get('data', [])
            
            # 检查任务锁定状态
            if tasks:
                tasks = self.check_task_lock(tasks, user_id, date)
                result['data']['data'] = tasks
            
            return result
            
        except Exception as e:
            log.error(f"获取任务列表失败: {e}")
            return {"code": -1, "msg": f"获取任务列表失败: {str(e)}", "data": None}

    def check_task_lock(self, tasks: List[Dict[str, Any]], user_id: Optional[int] = None, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        检查任务列表中的锁定状态
        
        Args:
            tasks: 任务列表
            user_id: 用户ID（可选）
            date_str: 日期字符串，格式 YYYY-MM-DD（可选）
            
        Returns:
            添加了 lock 和 msg 字段的任务列表
        """
        if not user_id or not date_str:
            # 如果没有用户ID或日期，返回原始任务列表
            for task in tasks:
                task['lock'] = False
                task['msg'] = ''
            return tasks
        
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            # 按优先级排序任务（数字越小优先级越高）
            sorted_tasks = sorted(tasks, key=lambda x: x.get('priority', 999))
            
            # 记录最高优先级的未完成任务
            highest_uncompleted_priority = None
            highest_uncompleted_task_name = None
            
            for task in sorted_tasks:
                priority = task.get('priority')
                
                # 如果任务没有优先级，不锁定
                if priority is None:
                    task['lock'] = False
                    task['msg'] = ''
                else:
                    # 如果有更高优先级（数字更小）的任务未完成，则锁定
                    if highest_uncompleted_priority is not None and priority > highest_uncompleted_priority:
                        task['lock'] = True
                        task['msg'] = f'请先完成 "{highest_uncompleted_task_name}"'
                    else:
                        task['lock'] = False
                        task['msg'] = ''
                
                # 检查 pre_todo 对应的日程是否完成
                pre_todo_str = task.get('pre_todo', '{}')
                pre_todo = json.loads(pre_todo_str) if isinstance(pre_todo_str, str) else pre_todo_str
                
                if pre_todo and isinstance(pre_todo, dict):
                    # pre_todo 格式: {"user_id": [todo_ids]}
                    todo_ids = pre_todo.get(str(user_id), [])
                    
                    if todo_ids and isinstance(todo_ids, list):
                        # 检查所有前置日程是否完成
                        all_completed, incomplete_names = self._check_schedules_completed(todo_ids, user_id, date_str)
                        
                        if not all_completed:
                            task['lock'] = True
                            task['msg'] = f'请先完成前置日程：{"、".join(incomplete_names)}'
                
                # 如果当前任务有未完成的素材，记录优先级
                if not task['lock'] and self._has_uncompleted_materials(task, user_id, target_date):
                    if highest_uncompleted_priority is None or (priority is not None and priority < highest_uncompleted_priority):
                        highest_uncompleted_priority = priority
                        highest_uncompleted_task_name = task.get('name', '')
            
            return tasks
            
        except Exception as e:
            log.error(f"检查任务锁定状态失败: {e}")
            # 出错时返回原始任务列表，不锁定
            for task in tasks:
                task['lock'] = False
                task['msg'] = ''
            return tasks
    
    def _has_uncompleted_materials(self, task: Dict[str, Any], user_id: int, target_date: datetime) -> bool:
        """
        检查任务在指定日期是否有未完成的素材
        
        Args:
            task: 任务数据
            user_id: 用户ID
            target_date: 目标日期
            
        Returns:
            True 如果有未完成的素材，False 否则
        """
        try:
            start_date = datetime.strptime(task.get('start_date', ''), '%Y-%m-%d')
            duration = task.get('duration', 0)
            day_offset = (target_date - start_date).days
            
            if day_offset < 0 or day_offset >= duration:
                return False
            
            # 解析任务数据
            task_data_str = task.get('data', '{}')
            task_data = json.loads(task_data_str) if isinstance(task_data_str, str) else task_data_str
            daily_materials = task_data.get('dailyMaterials', {})
            
            # type=1（持续任务）：所有素材都在第0天
            materials_index = 0 if task.get('type', 0) == 1 else day_offset
            materials_for_day = daily_materials.get(str(materials_index), [])
            
            if not materials_for_day:
                return False
            
            # 检查是否有任何素材未完成
            for material in materials_for_day:
                status = material.get('status', {})
                # 兼容旧格式或该用户未完成
                if isinstance(status, int) or status.get(str(user_id)) != 1:
                    return True
            
            return False
            
        except Exception as e:
            log.error(f"检查任务素材完成状态失败: {e}")
            return True
    
    def _check_schedules_completed(self, todo_ids: List[int], user_id: int, date_str: str) -> tuple:
        """
        检查前置日程是否都已完成
        
        Args:
            todo_ids: 日程ID列表
            user_id: 用户ID
            date_str: 日期字符串，格式 YYYY-MM-DD
            
        Returns:
            (bool, List[str]): (是否全部完成, 未完成的日程名称列表)
        """
        try:
            if not todo_ids:
                return True, []
            
            incomplete_names = []
            
            # 查询 t_schedule_save 表，检查这些日程在指定日期的完成状态
            for todo_id in todo_ids:
                result = db_mgr.query(
                    f"SELECT state FROM t_schedule_save WHERE schedule_id = {todo_id} AND date = '{date_str}'"
                )
                
                if result.get('code') != 0:
                    log.error(f"查询日程状态失败: {result.get('msg')}")
                    return False, [f'日程{todo_id}']
                
                saves = result.get('data', [])
                if not saves:
                    # 没有存档记录，视为未完成
                    # 获取日程名称
                    name_result = db_mgr.get_data('t_schedule', todo_id, 'name')
                    name = name_result.get('data', {}).get('name', f'日程{todo_id}') if name_result.get('code') == 0 else f'日程{todo_id}'
                    incomplete_names.append(name)
                    continue
                
                state = saves[0].get('state', 0)
                if state != 1:
                    # 有未完成的前置日程
                    # 获取日程名称
                    name_result = db_mgr.get_data('t_schedule', todo_id, 'name')
                    name = name_result.get('data', {}).get('name', f'日程{todo_id}') if name_result.get('code') == 0 else f'日程{todo_id}'
                    incomplete_names.append(name)
            
            # 所有前置日程都完成了
            return len(incomplete_names) == 0, incomplete_names
            
        except Exception as e:
            log.error(f"检查前置日程完成状态失败: {e}")
            return False, [f'日程{todo_id}' for todo_id in todo_ids]


task_mgr = TaskMgr()
