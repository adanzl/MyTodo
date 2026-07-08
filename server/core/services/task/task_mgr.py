"""
素材管理服务
提供素材的增删改查功能
"""
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta, date
import calendar as calendar_module
import json
import time

from flask import current_app

from core.config import app_logger
from core.config.const import DEFAULT_BASE_DIR
from core.db.db_mgr import db_mgr
from core.db import rds_mgr
from core.tools.async_util import run_in_background
from core.utils import get_media_duration, validate_and_normalize_path
from .block_time import is_global_block_time_now, parse_block_time_config, _get_user_entry, _is_blocked_by_entry
from .rest_days import parse_rest_days, is_rest_day, get_workday_index, end_date_by_work_duration

log = app_logger

TABLE_MATERIAL = 't_material'
TABLE_TASK = 't_task'
TABLE_MATERIAL_CATEGORY = 't_material_category'


class TaskMgr:
    """任务管理器 - 素材管理"""

    def __init__(self) -> None:
        pass

    @staticmethod
    def _is_material_completed_for_user(material: Dict[str, Any], user_id: Optional[int]) -> bool:
        """判断素材对指定用户是否已完成打卡。"""
        status = material.get('status')
        if not isinstance(status, dict):
            return False
        if user_id and user_id > 0:
            return status.get(str(user_id)) == 1
        return any(v == 1 for v in status.values())

    def get_task_calendar(self, date_str: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """获取指定月份的任务日历，包含每日素材列表与锁定状态。"""
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

            result = db_mgr.get_list(
                TABLE_TASK, page_num=1, page_size=1000, conditions=conditions)
            if result.get('code') != 0:
                log.error(f"获取任务列表失败: {result.get('msg')}")
                return {"code": -1, "msg": "获取任务列表失败", "data": None}

            tasks = result.get('data', {}).get('data', [])
            if user_id and user_id > 0:
                tasks = self.check_task_lock(tasks, user_id, date_str)

            calendar_data: Dict[str, Dict[str, Any]] = {}
            for task in tasks:
                try:
                    start_date_str = task.get('start_date', '')
                    duration = task.get('duration', 0)
                    task_type = task.get('type', 0)
                    if not start_date_str or duration <= 0:
                        continue

                    start_date_d = datetime.strptime(
                        start_date_str, '%Y-%m-%d').date()
                    task_data = json.loads(task.get('data') or '{}')
                    daily_materials = task_data.get('dailyMaterials', {})
                    pre_todo = json.loads(task.get('pre_todo') or '{}')
                    rule = parse_rest_days(task.get("rest_days"))
                    end_d = end_date_by_work_duration(
                        start_date_d, int(duration), rule)

                    cur = start_date_d
                    while cur <= end_d:
                        if cur.month != month or cur.year != year:
                            cur = cur + timedelta(days=1)
                            continue
                        date_key = cur.strftime('%Y-%m-%d')
                        if date_key not in calendar_data:
                            calendar_data[date_key] = {
                                'date': date_key, 'tasks': []}

                        if is_rest_day(rule, cur):
                            materials_for_day = []
                        else:
                            workday_idx = get_workday_index(
                                start_date_d, cur, rule)
                            materials_index = 0 if task_type == 1 else workday_idx
                            materials_for_day = daily_materials.get(str(materials_index), []) if isinstance(
                                daily_materials, dict) else []
                        total_count = len(materials_for_day)
                        completed_count = sum(
                            1 for m in materials_for_day
                            if isinstance(m, dict) and self._is_material_completed_for_user(m, user_id))

                        calendar_data[date_key]['tasks'].append({
                            'task_id': task.get('id'),
                            'task_name': task.get('name', ''),
                            'total': total_count,
                            'completed': completed_count,
                            'materials': materials_for_day,
                            'pre_todo': pre_todo,
                            'lock': task.get('lock', False),
                            'msg': task.get('msg', '')
                        })
                        cur = cur + timedelta(days=1)
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
        """完成指定日期的素材打卡，并在当天全部完成时发放积分。"""
        try:
            task_result = db_mgr.get_data(TABLE_TASK, task_id, '*')
            if task_result.get('code') != 0 or not task_result.get('data'):
                return {"code": -1, "msg": "任务不存在", "data": None}

            task = task_result['data']
            task_data = json.loads(task.get('data') or '{}')
            daily_materials = task_data.get('dailyMaterials', {})

            start_date_str = task.get('start_date', '')
            if not start_date_str:
                return {"code": -1, "msg": "任务开始日期不存在", "data": None}

            start_date_d = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            target_d = datetime.strptime(date_str, '%Y-%m-%d').date()
            duration = int(task.get("duration", 0) or 0)
            if duration <= 0:
                return {"code": -1, "msg": "任务天数不存在", "data": None}

            rule = parse_rest_days(task.get("rest_days"))
            workday_idx = get_workday_index(start_date_d, target_d, rule)
            if workday_idx == -1:
                return {"code": -1, "msg": "日期不在任务范围内", "data": None}
            if workday_idx == -2:
                return {"code": -1, "msg": "休息日不能打卡", "data": None}
            if workday_idx >= duration:
                return {"code": -1, "msg": "日期不在任务范围内", "data": None}

            materials_index = 0 if task.get('type', 0) == 1 else workday_idx
            materials_for_day = daily_materials.get(str(materials_index), [])

            for material in materials_for_day:
                if material.get('id') == material_id:
                    material.setdefault('status', {})
                    material['status'][str(user_id)] = 1
                    break
            else:
                return {"code": -1, "msg": "素材不存在于该天", "data": None}

            task_data['dailyMaterials'] = daily_materials
            updated_data = json.dumps(task_data, ensure_ascii=False)
            update_result = db_mgr.set_data(
                TABLE_TASK, {'id': task_id, 'data': updated_data})
            if update_result.get('code') != 0:
                return {"code": -1, "msg": "更新失败", "data": None}

            history_data = {
                'user_id': user_id,
                'task_id': task_id,
                'material_id': material_id,
                'date_str': date_str,
                'state': 1,
                'reward': 0
            }
            history_result = db_mgr.set_data('t_task_history', history_data)
            if history_result.get('code') != 0:
                log.error(f"插入任务历史记录失败: {history_result.get('msg')}")

            all_completed = all(
                self._is_material_completed_for_user(m, user_id)
                for m in materials_for_day if isinstance(m, dict)
            )
            score_added = 0
            if all_completed:
                score = task_data.get('dailyScore', {}).get(
                    str(materials_index), 0)
                if score > 0:
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
        """删除素材分类（文件夹）"""
        try:

            def get_all_children_ids(parent_id: int) -> List[int]:
                children_ids: List[int] = []
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
                            children_ids.extend(get_all_children_ids(child_id))
                return children_ids

            all_category_ids = [category_id] + \
                get_all_children_ids(category_id)

            # 不删除素材：检查是否有素材
            if not delete_materials:
                for cat_id in all_category_ids:
                    materials_result = db_mgr.get_list(TABLE_MATERIAL,
                                                       page_num=1,
                                                       page_size=1,
                                                       conditions={'cate_id': cat_id})
                    if materials_result.get('code') == 0 and materials_result.get('data', {}).get('total', 0) > 0:
                        return {"code": -1, "msg": "该目录或其子目录下还有素材，无法删除（可勾选'同时删除素材'）", "data": None}

            # 删除素材：先删除所有类别下的素材
            if delete_materials:
                for cat_id in all_category_ids:
                    materials_result = db_mgr.get_list(TABLE_MATERIAL,
                                                       page_num=1,
                                                       page_size=1000,
                                                       conditions={'cate_id': cat_id})
                    if materials_result.get('code') == 0:
                        materials = materials_result.get(
                            'data', {}).get('data', [])
                        for material in materials:
                            material_id = material.get('id')
                            if material_id is not None:
                                db_mgr.del_data(TABLE_MATERIAL, material_id)

            # 从叶子节点开始删除类别
            all_category_ids.reverse()
            for cat_id in all_category_ids:
                result = db_mgr.del_data(TABLE_MATERIAL_CATEGORY, cat_id)
                if result.get('code') != 0:
                    return {"code": -1, "msg": f"删除分类 {cat_id} 失败: {result.get('msg')}", "data": None}

            return {"code": 0, "msg": "删除成功", "data": None}
        except Exception as e:
            log.error(f'删除素材分类失败: {e}')
            return {"code": -1, "msg": f"删除失败: {str(e)}", "data": None}

    def get_task_list(self,
                      user_id: Optional[int] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      page_num: int = 1,
                      page_size: int = 20) -> Dict[str, Any]:
        """分页获取任务列表，并按日期计算各任务的锁定状态。"""
        try:
            if start_date and not end_date:
                end_date = start_date

            conditions: Dict[str, Any] = {}
            if user_id and user_id > 0:
                conditions['user_id'] = {'like': f'%{user_id}%'}
            if start_date and end_date:
                conditions['start_date'] = {'<=': end_date}
                conditions['end_date'] = {'>=': start_date}

            result = db_mgr.get_list(
                TABLE_TASK, page_num=page_num, page_size=page_size, conditions=conditions)
            if result.get('code') != 0:
                return result

            tasks = result.get('data', {}).get('data', [])
            if tasks:
                tasks = self.check_task_lock(tasks, user_id, start_date)
                result['data']['data'] = tasks
            return result
        except Exception as e:
            log.error(f"获取任务列表失败: {e}")
            return {"code": -1, "msg": f"获取任务列表失败: {str(e)}", "data": None}

    def update_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建或更新任务，自动序列化 JSON 字段并计算结束日期。"""
        try:
            task_id = task_data.get('id')
            if task_id is None or task_id <= 0:
                task_data = {k: v for k, v in task_data.items() if k != 'id'}

            start_d = datetime.strptime(
                task_data["start_date"], "%Y-%m-%d").date()
            dur = int(task_data["duration"])
            rest_days_raw = task_data.get("rest_days")
            if isinstance(rest_days_raw, dict):
                rest_days_raw = json.dumps(rest_days_raw, ensure_ascii=False)
                task_data["rest_days"] = rest_days_raw
            block_time_raw = task_data.get("block_time")
            if isinstance(block_time_raw, (list, dict)):
                task_data["block_time"] = json.dumps(
                    block_time_raw, ensure_ascii=False)
            data_raw = task_data.get("data")
            if isinstance(data_raw, dict):
                task_data["data"] = json.dumps(data_raw, ensure_ascii=False)
            rule = parse_rest_days(rest_days_raw)
            task_data["end_date"] = end_date_by_work_duration(
                start_d, dur, rule).strftime("%Y-%m-%d")

            res = db_mgr.set_data(TABLE_TASK, task_data)
            if res.get("code") != 0:
                return res
            tid = res.get("data")
            return db_mgr.get_data(TABLE_TASK, int(tid), "*") if tid else {"code": 0, "msg": "ok", "data": None}
        except Exception as e:
            log.error(f"update_task failed: {e}")
            return {"code": -1, "msg": f"update_task failed: {str(e)}", "data": None}

    def get_material_parent_chain(self, material_id: int) -> Dict[str, Any]:
        """获取素材的父目录链（从当前目录到根目录）"""
        try:
            material = db_mgr.get_data(TABLE_MATERIAL, material_id, '*')
            if material.get('code') != 0 or not material.get('data'):
                return {"code": -1, "msg": "素材不存在", "data": None}

            cate_id = material['data'].get('cate_id', -1)
            if cate_id == -1 or cate_id is None:
                return {"code": 0, "msg": "success", "data": [{"id": -1, "name": "根目录", "parent": None}]}

            chain = []
            current_id = cate_id
            visited = set()
            while current_id != -1 and current_id not in visited:
                visited.add(current_id)
                category = db_mgr.get_data(
                    TABLE_MATERIAL_CATEGORY, current_id, '*')
                if category.get('code') != 0 or not category.get('data'):
                    break
                cat_data = category['data']
                chain.append(
                    {"id": cat_data['id'], "name": cat_data['name'], "parent": cat_data.get('parent', -1)})
                current_id = cat_data.get('parent', -1)

            chain.append({"id": -1, "name": "根目录", "parent": None})
            chain.reverse()
            return {"code": 0, "msg": "success", "data": chain}
        except Exception as e:
            log.error(f'获取素材父目录链失败: {e}')
            return {"code": -1, "msg": f"获取失败: {str(e)}", "data": None}

    def get_material_status(self, user_id: int, material_id: int, task_id: Optional[int] = None) -> Dict[str, Any]:
        """获取视频素材的锁定状态（需观看达到时长后才解锁）。

        Args:
            user_id: 用户ID
            material_id: 素材ID
            task_id: 任务ID（可选，用于检查任务级白名单）

        优先级：任务级 block_time 配置优先于全局配置。
        """
        try:
            # 实时检查白名单（任务级优先于全局）
            now = datetime.now()
            date_str = now.strftime('%Y-%m-%d')

            # 1. 先检查任务级 block_time（任务配置优先于全局）
            if task_id and task_id > 0:
                task_res = db_mgr.get_data(TABLE_TASK, task_id, 'block_time')
                if task_res.get('code') == 0 and task_res.get('data'):
                    block_time_raw = task_res['data'].get('block_time', '{}')
                    config = parse_block_time_config(block_time_raw)
                    task_entry = _get_user_entry(config, user_id)
                    if task_entry is not None:
                        # 任务有此用户的 block_time 配置 → 以任务配置为准
                        if _is_blocked_by_entry(task_entry, now):
                            return {"code": 0, "msg": "ok", "data": {"lock": True, "reason": "当前处于任务禁用时段"}}
                        # 任务配置允许 → 不锁，跳过全局检查
                    else:
                        # 任务无此用户的配置 → 回退到全局检查
                        if is_global_block_time_now(date_str, user_id, now=now):
                            return {"code": 0, "msg": "ok", "data": {"lock": True, "reason": "当前处于全局禁用时段"}}
                else:
                    # 任务无 block_time 配置 → 回退到全局检查
                    if is_global_block_time_now(date_str, user_id, now=now):
                        return {"code": 0, "msg": "ok", "data": {"lock": True, "reason": "当前处于全局禁用时段"}}
            else:
                # 无 task_id → 只检查全局
                if is_global_block_time_now(date_str, user_id, now=now):
                    return {"code": 0, "msg": "ok", "data": {"lock": True, "reason": "当前处于全局禁用时段"}}

            res = db_mgr.get_data(
                TABLE_MATERIAL, material_id, 'type,duration,statistics,path')
            if res.get('code') != 0:
                return {"code": -1, "msg": "素材不存在", "data": {"lock": False}}

            mat = res['data']
            if mat.get('type') != 1:
                return {"code": 0, "msg": "ok", "data": {"lock": False}}

            material_duration = mat.get('duration')
            if not material_duration:
                path = mat.get('path')
                if path:
                    # type: ignore[attr-defined]
                    app = current_app._get_current_object()
                    mid = material_id

                    def _fetch(fp=path, m_id=mid):
                        with app.app_context():
                            p, _ = validate_and_normalize_path(
                                fp, DEFAULT_BASE_DIR, must_be_file=True)
                            d = get_media_duration(p) if p else None
                            if d:
                                db_mgr.set_data(TABLE_MATERIAL, {
                                                'id': m_id, 'duration': d})

                    run_in_background(_fetch)
                return {"code": 0, "msg": "ok", "data": {"lock": False}}

            # 检查是否存在有效的不限时记录（用户维度，不区分素材）
            active_unlimit = TaskMgr._get_active_unlimit(user_id)
            if active_unlimit:
                return {"code": 0, "msg": "ok", "data": {"lock": False, "duration": material_duration, "unlimit": True}}

            stats = mat.get('statistics') or {}
            if isinstance(stats, str):
                stats = json.loads(stats)
            locked = int(stats.get(str(user_id), 0)
                         or 0) >= float(material_duration) * 1.2
            return {"code": 0, "msg": "ok", "data": {"lock": locked, "duration": material_duration}}
        except Exception as e:
            log.error(f"获取素材状态失败: material_id={material_id}, {e}")
            return {"code": -1, "msg": f"获取失败: {str(e)}", "data": {"lock": False}}

    @staticmethod
    def _unlimit_rds_key(user_id: int) -> str:
        return f"task:unlimit:{user_id}"

    @staticmethod
    def _get_active_unlimit(user_id: int) -> Optional[Dict[str, Any]]:
        """检查用户是否存在有效的不限时记录。"""
        key = TaskMgr._unlimit_rds_key(user_id)
        raw = rds_mgr.get_str(key)
        if not raw:
            return None
        try:
            record = json.loads(raw)
            expiry_ts = record.get('expiry_ts', 0)
            if time.time() >= expiry_ts:
                # 已过期，清理
                return None
            return record
        except (json.JSONDecodeError, KeyError):
            return None

    def apply_unlimit(
        self,
        user_id: int,
        material_id: int,
        task_id: Optional[int] = None,
        duration_hours: float = 1.0,
    ) -> Dict[str, Any]:
        """提交不限时申请（需管理员审批后生效）。

        Args:
            user_id: 用户ID
            material_id: 素材ID（记录用途）
            task_id: 任务ID（可选，记录用途）
            duration_hours: 申请不限时时长（小时）
        """
        try:
            apply_id = int(time.time() * 1000)
            record = {
                'id': apply_id,
                'user_id': user_id,
                'material_id': material_id,
                'task_id': task_id,
                'duration_hours': duration_hours,
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
            }
            # 存储申请记录
            apply_key = f"task:unlimit:apply:{apply_id}"
            rds_mgr.set(apply_key, json.dumps(record, ensure_ascii=False))

            # 加入待审批索引
            self._add_to_pending_index(apply_id, record)

            log.info(
                f"不限时申请已提交: id={apply_id} user={user_id} "
                f"material={material_id} duration={duration_hours}h"
            )
            return {"code": 0, "msg": "申请已提交，等待管理员审批", "data": {"success": True, "id": apply_id}}
        except Exception as e:
            log.error(f"不限时申请提交失败: user={user_id} material={material_id}, {e}")
            return {"code": -1, "msg": f"申请失败: {str(e)}"}

    PENDING_INDEX_KEY = "task:unlimit:apply:pending"

    @staticmethod
    def _add_to_pending_index(apply_id: int, record: Dict[str, Any]) -> None:
        """将申请加入待审批索引列表。"""
        raw = rds_mgr.get_str(TaskMgr.PENDING_INDEX_KEY)
        pending: List[Dict[str, Any]] = json.loads(raw) if raw else []
        pending.append({
            'id': apply_id,
            'user_id': record.get('user_id'),
            'material_id': record.get('material_id'),
            'task_id': record.get('task_id'),
            'duration_hours': record.get('duration_hours'),
            'status': 'pending',
            'created_at': record.get('created_at'),
        })
        rds_mgr.set(TaskMgr.PENDING_INDEX_KEY, json.dumps(pending, ensure_ascii=False))

    def list_unlimit_applications(self, status: Optional[str] = None) -> Dict[str, Any]:
        """列出不限时申请（默认只返回待审批的）。

        Args:
            status: 过滤状态，None 或 'pending' 返回待审批
        """
        try:
            raw = rds_mgr.get_str(TaskMgr.PENDING_INDEX_KEY)
            all_apps: List[Dict[str, Any]] = json.loads(raw) if raw else []
            if status:
                all_apps = [a for a in all_apps if a.get('status') == status]
            else:
                all_apps = [a for a in all_apps if a.get('status') == 'pending']
            return {"code": 0, "msg": "ok", "data": {"applications": all_apps, "total": len(all_apps)}}
        except Exception as e:
            log.error(f"列出不限时申请失败: {e}")
            return {"code": -1, "msg": f"查询失败: {str(e)}"}

    def approve_unlimit(self, ids: List[int]) -> Dict[str, Any]:
        """批量审批通过不限时申请。"""
        try:
            raw = rds_mgr.get_str(TaskMgr.PENDING_INDEX_KEY)
            pending: List[Dict[str, Any]] = json.loads(raw) if raw else []
            approved_count = 0
            not_found_ids: List[int] = []

            for apply_id in ids:
                found = False
                for item in pending:
                    if item.get('id') == apply_id and item.get('status') == 'pending':
                        found = True
                        # 读取完整申请记录
                        apply_key = f"task:unlimit:apply:{apply_id}"
                        apply_raw = rds_mgr.get_str(apply_key)
                        if apply_raw:
                            record = json.loads(apply_raw)
                            record['status'] = 'approved'
                            record['approved_at'] = datetime.now().isoformat()
                            # 更新记录
                            rds_mgr.set(apply_key, json.dumps(record, ensure_ascii=False))

                            # 设置活跃不限时状态（结束时间 = 审批时间 + 时长）
                            now_ts = time.time()
                            expiry_ts = now_ts + record.get('duration_hours', 1) * 3600
                            expires_at = datetime.fromtimestamp(expiry_ts).isoformat()
                            unlimit_record = {
                                'user_id': record['user_id'],
                                'apply_id': apply_id,
                                'duration_hours': record.get('duration_hours'),
                                'expiry_ts': expiry_ts,
                                'expires_at': expires_at,
                                'approved_at': datetime.now().isoformat(),
                            }
                            unlimit_key = TaskMgr._unlimit_rds_key(record['user_id'])
                            rds_mgr.set(unlimit_key, json.dumps(unlimit_record, ensure_ascii=False))

                        # 更新索引中的状态
                        item['status'] = 'approved'
                        item['approved_at'] = datetime.now().isoformat()
                        approved_count += 1
                        break

                if not found:
                    not_found_ids.append(apply_id)

            # 写回索引
            rds_mgr.set(TaskMgr.PENDING_INDEX_KEY, json.dumps(pending, ensure_ascii=False))

            log.info(f"不限时审批通过: ids={ids} approved={approved_count} not_found={not_found_ids}")
            return {
                "code": 0, "msg": "ok",
                "data": {"approved": approved_count, "not_found": not_found_ids}
            }
        except Exception as e:
            log.error(f"不限时审批失败: {e}")
            return {"code": -1, "msg": f"审批失败: {str(e)}"}

    def deny_unlimit(self, ids: List[int]) -> Dict[str, Any]:
        """批量拒绝不限时申请。"""
        try:
            raw = rds_mgr.get_str(TaskMgr.PENDING_INDEX_KEY)
            pending: List[Dict[str, Any]] = json.loads(raw) if raw else []
            denied_count = 0
            not_found_ids: List[int] = []

            for apply_id in ids:
                found = False
                for item in pending:
                    if item.get('id') == apply_id and item.get('status') == 'pending':
                        found = True
                        # 更新申请记录
                        apply_key = f"task:unlimit:apply:{apply_id}"
                        apply_raw = rds_mgr.get_str(apply_key)
                        if apply_raw:
                            record = json.loads(apply_raw)
                            record['status'] = 'denied'
                            record['denied_at'] = datetime.now().isoformat()
                            rds_mgr.set(apply_key, json.dumps(record, ensure_ascii=False))

                        # 更新索引中的状态
                        item['status'] = 'denied'
                        item['denied_at'] = datetime.now().isoformat()
                        denied_count += 1
                        break

                if not found:
                    not_found_ids.append(apply_id)

            # 写回索引
            rds_mgr.set(TaskMgr.PENDING_INDEX_KEY, json.dumps(pending, ensure_ascii=False))

            log.info(f"不限时申请已拒绝: ids={ids} denied={denied_count} not_found={not_found_ids}")
            return {
                "code": 0, "msg": "ok",
                "data": {"denied": denied_count, "not_found": not_found_ids}
            }
        except Exception as e:
            log.error(f"不限时拒绝失败: {e}")
            return {"code": -1, "msg": f"拒绝失败: {str(e)}"}

    def check_task_lock(self,
                        tasks: List[Dict[str, Any]],
                        user_id: Optional[int] = None,
                        date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """为任务列表计算锁定状态，写入 lock 与 msg 字段。

        锁定规则（按优先级依次判断）：
        1. 存在更高优先级（数值更小）的未完成任务（priority=-1 的任务不参与此项）
        2. 前置日程未完成
        3. 前置任务在当天仍有未完成打卡

        注意：block_time 校验不在此处处理，由 /material/status 接口单独负责。
        """
        if not user_id or not date_str:
            for task in tasks:
                task['lock'] = False
                task['msg'] = ''
            return tasks

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            task_by_id = {t['id']: t for t in tasks if t.get('id')}
            sorted_tasks = sorted(tasks, key=lambda x: x.get('priority', 999))
            highest_uncompleted_priority = None
            highest_uncompleted_task_name = None

            for task in sorted_tasks:
                priority = task.get('priority')
                priority_excluded = priority == -1
                if (not priority_excluded and highest_uncompleted_priority is not None
                        and priority is not None and priority > highest_uncompleted_priority):
                    task['lock'] = True
                    task['msg'] = f'请先完成 "{highest_uncompleted_task_name}"'
                else:
                    task['lock'] = False
                    task['msg'] = ''

                pre_todo_raw = task.get('pre_todo') or '{}'
                pre_todo = pre_todo_raw if isinstance(
                    pre_todo_raw, dict) else json.loads(pre_todo_raw)
                if isinstance(pre_todo, dict) and pre_todo:
                    todo_ids = pre_todo.get(str(user_id), [])
                    if todo_ids:
                        all_completed, incomplete_names = self._check_schedules_completed(
                            todo_ids, user_id, date_str)
                        if not all_completed:
                            task['lock'] = True
                            task['msg'] = f'请先完成前置日程：{"、".join(incomplete_names)}'

                if not task.get('lock'):
                    pre_task_raw = task.get('pre_task')
                    if pre_task_raw:
                        pre_task_ids = pre_task_raw if isinstance(
                            pre_task_raw, list) else json.loads(pre_task_raw)
                        for tid in pre_task_ids:
                            if tid == task.get('id'):
                                continue
                            pre = task_by_id.get(tid)
                            # 仅检查前置任务在 date_str 当天的打卡是否完成
                            if pre and self._has_uncompleted_materials(pre, user_id, target_date):
                                task['lock'] = True
                                task['msg'] = f'请先完成前置任务：{pre.get("name", f"任务{tid}")}'
                                break

                if (not priority_excluded and not task['lock']
                        and self._has_uncompleted_materials(task, user_id, target_date)):
                    if highest_uncompleted_priority is None or (priority is not None
                                                                and priority < highest_uncompleted_priority):
                        highest_uncompleted_priority = priority
                        highest_uncompleted_task_name = task.get('name', '')

            return tasks
        except Exception as e:
            log.error(f"检查任务锁定状态失败: {e}")
            for task in tasks:
                task['lock'] = False
                task['msg'] = ''
            return tasks

    def _has_uncompleted_materials(self, task: Dict[str, Any], user_id: int, target_date: datetime) -> bool:
        """判断任务在指定日期是否仍有未完成的素材。"""
        try:
            start_date_str = task.get('start_date', '')
            if not start_date_str:
                return False
            start_date_d = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            duration = int(task.get('duration', 0) or 0)
            if duration <= 0:
                return False

            target_d = target_date.date()
            rule = parse_rest_days(task.get('rest_days'))
            workday_idx = get_workday_index(start_date_d, target_d, rule)
            if workday_idx == -2:
                return False
            if workday_idx < 0 or workday_idx >= duration:
                return False

            task_data = json.loads(task.get('data') or '{}')
            daily_materials = task_data.get('dailyMaterials', {})
            materials_index = 0 if task.get('type', 0) == 1 else workday_idx
            materials_for_day = daily_materials.get(str(materials_index), [])
            if not materials_for_day:
                return False
            return any(
                isinstance(m, dict) and not self._is_material_completed_for_user(
                    m, user_id)
                for m in materials_for_day
            )
        except Exception as e:
            log.error(f"检查任务素材完成状态失败: {e}")
            return True

    def _check_schedules_completed(self, todo_ids: List[int], user_id: int, date_str: str) -> tuple:
        """检查前置日程在指定日期是否全部完成。

        Returns:
            (是否全部完成, 未完成日程名称列表)
        """
        try:
            if not todo_ids:
                return True, []
            incomplete_names = []
            for todo_id in todo_ids:
                result = db_mgr.query(
                    f"SELECT state FROM t_schedule_save WHERE schedule_id = {todo_id} AND date = '{date_str}'")
                if result.get('code') != 0:
                    return False, [f'日程{todo_id}']
                saves = result.get('data', [])
                if not saves or saves[0].get('state', 0) != 1:
                    name_result = db_mgr.get_data(
                        't_schedule', todo_id, 'title')
                    name = name_result.get('data', {}).get(
                        'title', f'日程{todo_id}') if name_result.get('code') == 0 else f'日程{todo_id}'
                    incomplete_names.append(name)
            return len(incomplete_names) == 0, incomplete_names
        except Exception as e:
            log.error(f"检查前置日程完成状态失败: {e}")
            return False, [f'日程{todo_id}' for todo_id in todo_ids]


task_mgr = TaskMgr()
