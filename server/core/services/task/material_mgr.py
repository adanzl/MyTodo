"""素材管理服务。

提供素材锁定状态、不限时申请审批、分类管理等功能的业务逻辑。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import current_app

from core.config import app_logger
from core.config.const import DEFAULT_BASE_DIR
from core.db.db_mgr import db_mgr
from core.tools.async_util import run_in_background
from core.utils import get_media_duration, validate_and_normalize_path
from .block_time import is_global_block_time_now, parse_block_time_config, _get_user_entry, _is_blocked_by_entry

log = app_logger

TABLE_MATERIAL = 't_material'
TABLE_TASK = 't_task'
TABLE_MATERIAL_CATEGORY = 't_material_category'
TABLE_UNLIMIT = 't_material_unlimit'

_ok = lambda data: {"code": 0, "msg": "ok", "data": data}
_err = lambda msg, data: {"code": -1, "msg": msg, "data": data}


def _ts(minutes: int = 0) -> str:
    """返回带时区偏移的时间字符串，如 '2026-07-09 12:34:56 +08:00'。minutes>0 表示当前时间之后的分钟。"""
    dt = datetime.now() + timedelta(minutes=minutes)
    offset = dt.astimezone().utcoffset()
    hours = int(offset.total_seconds() / 3600) if offset else 0
    return dt.strftime(f'%Y-%m-%d %H:%M:%S {hours:+03d}:00')


class MaterialMgr:
    """素材管理器"""

    LOCK_CODE_NONE = 0  # 未锁定
    LOCK_CODE_TASK_BLOCK = 1  # 任务级禁用时段
    LOCK_CODE_GLOBAL_BLOCK = 2  # 全局禁用时段
    LOCK_CODE_DURATION = 3  # 视频观看时长超限

    @staticmethod
    def _get_active_unlimit(user_id: int,
                            material_id: int = 0,
                            task_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """检查用户是否存在有效的不限时记录。"""
        try:
            now_iso = _ts()
            base = {
                'user_id': user_id,
                'status': 'approved',
                'expires_at': {
                    '>': now_iso
                },
            }
            # 1/2=用户级不限时
            r = db_mgr.get_list(TABLE_UNLIMIT, page_size=1, conditions={**base, 'lock_code': {'in': [1, 2]}})
            if r.get('code') == 0 and r.get('data', {}).get('data'):
                return r['data']['data'][0]
            # 3=素材级不限时，需匹配素材和任务
            r = db_mgr.get_list(TABLE_UNLIMIT,
                                page_size=1,
                                conditions={
                                    **base, 'lock_code': 3,
                                    'material_id': material_id,
                                    'task_id': task_id
                                })
            if r.get('code') == 0 and r.get('data', {}).get('data'):
                return r['data']['data'][0]
            return None
        except Exception:
            return None

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

            all_category_ids = [category_id] + get_all_children_ids(category_id)

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
                        materials = materials_result.get('data', {}).get('data', [])
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
                category = db_mgr.get_data(TABLE_MATERIAL_CATEGORY, current_id, '*')
                if category.get('code') != 0 or not category.get('data'):
                    break
                cat_data = category['data']
                chain.append({"id": cat_data['id'], "name": cat_data['name'], "parent": cat_data.get('parent', -1)})
                current_id = cat_data.get('parent', -1)

            chain.append({"id": -1, "name": "根目录", "parent": None})
            chain.reverse()
            return {"code": 0, "msg": "success", "data": chain}
        except Exception as e:
            log.error(f'获取素材父目录链失败: {e}')
            return {"code": -1, "msg": f"获取失败: {str(e)}", "data": None}

    def get_material_status(self, user_id: int, material_id: int, task_id: Optional[int] = None) -> Dict[str, Any]:
        """获取素材的锁定状态。

        lock 返回值说明：
            0  = 未锁定
            1  = 任务级禁用时段
            2  = 全局禁用时段
            3  = 视频观看时长超限（≥120%）

        Args:
            user_id: 用户ID
            material_id: 素材ID
            task_id: 任务ID（可选，用于检查任务级白名单）

        优先级：任务级 block_time 配置优先于全局配置。
        """
        try:
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
                            return _ok({"lock": MaterialMgr.LOCK_CODE_TASK_BLOCK, "reason": "当前处于任务禁用时段"})
                    else:
                        # 任务无此用户的配置 → 回退到全局检查
                        if is_global_block_time_now(date_str, user_id, now=now):
                            return _ok({"lock": MaterialMgr.LOCK_CODE_GLOBAL_BLOCK, "reason": "当前处于全局禁用时段"})
                else:
                    # 任务无 block_time 配置 → 回退到全局检查
                    if is_global_block_time_now(date_str, user_id, now=now):
                        return _ok({"lock": MaterialMgr.LOCK_CODE_GLOBAL_BLOCK, "reason": "当前处于全局禁用时段"})
            else:
                # 无 task_id → 只检查全局
                if is_global_block_time_now(date_str, user_id, now=now):
                    return _ok({"lock": MaterialMgr.LOCK_CODE_GLOBAL_BLOCK, "reason": "当前处于全局禁用时段"})

            res = db_mgr.get_data(TABLE_MATERIAL, material_id, 'type,duration,statistics,path')
            if res.get('code') != 0:
                return _err("素材不存在", {"lock": MaterialMgr.LOCK_CODE_NONE})

            mat = res['data']
            if mat.get('type') != 1:
                return _ok({"lock": MaterialMgr.LOCK_CODE_NONE})

            material_duration = mat.get('duration')
            if not material_duration:
                path = mat.get('path')
                if path:
                    app = current_app._get_current_object()  # type: ignore[attr-defined]
                    mid = material_id

                    def _fetch(fp=path, m_id=mid):
                        with app.app_context():
                            p, _ = validate_and_normalize_path(fp, DEFAULT_BASE_DIR, must_be_file=True)
                            d = get_media_duration(p) if p else None
                            if d:
                                db_mgr.set_data(TABLE_MATERIAL, {'id': m_id, 'duration': d})

                    run_in_background(_fetch)
                return _ok({"lock": MaterialMgr.LOCK_CODE_NONE})

            # 检查是否存在有效的不限时记录
            active_unlimit = MaterialMgr._get_active_unlimit(user_id, material_id, task_id)
            if active_unlimit:
                return _ok({"lock": MaterialMgr.LOCK_CODE_NONE, "duration": material_duration, "unlimit": True})

            stats = mat.get('statistics') or {}
            if isinstance(stats, str):
                stats = json.loads(stats)
            user_stats = int(stats.get(str(user_id), 0) or 0)
            if user_stats >= float(material_duration) * 1.2:
                return _ok({
                    "lock": MaterialMgr.LOCK_CODE_DURATION,
                    "reason": "观看时长超限 " + str(user_stats) + "s",
                    "duration": material_duration
                })
            return _ok({"lock": MaterialMgr.LOCK_CODE_NONE, "duration": material_duration})
        except Exception as e:
            log.error(f"获取素材状态失败: material_id={material_id}, {e}")
            return _err(f"获取失败: {str(e)}", {"lock": MaterialMgr.LOCK_CODE_NONE})

    def apply_unlimit(
        self,
        user_id: int,
        material_id: int,
        task_id: int,
        duration: int = 60,
        lock_code: int = 0,
    ) -> Dict[str, Any]:
        """提交不限时申请（需管理员审批后生效）。

        Args:
            user_id: 用户ID
            material_id: 素材ID（记录用途）
            task_id: 任务ID（可选，记录用途）
            duration: 申请不限时时长（分钟）
            lock_code: 锁定类型码（0=未锁定, 1=任务禁用, 2=全局禁用, 3=时长超限）
        """
        try:
            now_iso = _ts()

            # 去重逻辑：按 lock_code 类型区分替换范围
            if lock_code == 3:
                # 3=时长超限：按 (user_id, material_id, task_id) 去重
                cond: Dict[str, Any] = {
                    'user_id': user_id,
                    'status': 'pending',
                    'lock_code': 3,
                    'material_id': material_id,
                    'task_id': task_id,
                }
                pending_res = db_mgr.get_list(TABLE_UNLIMIT, page_size=10, conditions=cond)
            else:
                # 1/2=禁用时段：按 user_id 去重（不限素材/任务）
                pending_res = db_mgr.get_list(TABLE_UNLIMIT,
                                              page_size=10,
                                              conditions={
                                                  'user_id': user_id,
                                                  'status': 'pending',
                                                  'lock_code': {
                                                      'in': [1, 2]
                                                  },
                                              })
            if pending_res.get('code') == 0:
                records = pending_res.get('data', {}).get('data', [])
                if records:
                    old = records[0]
                    old_id = old.get('id')
                    if old_id:
                        db_mgr.set_data(
                            TABLE_UNLIMIT, {
                                'id': old_id,
                                'duration': duration,
                                'material_id': material_id,
                                'task_id': task_id,
                                'created_at': now_iso,
                            })
                        apply_id = old_id
                        log.info(f"不限时申请已更新: id={apply_id} user={user_id} "
                                 f"material={material_id} duration={duration}min")
                        return {
                            "code": 0,
                            "msg": "申请已更新，等待管理员审批",
                            "data": {
                                "success": True,
                                "id": apply_id,
                                "replaced": True
                            }
                        }

            # 插入新申请
            result = db_mgr.set_data(
                TABLE_UNLIMIT, {
                    'user_id': user_id,
                    'material_id': material_id,
                    'task_id': task_id,
                    'duration': duration,
                    'type': 0,
                    'lock_code': lock_code,
                    'status': 'pending',
                    'created_at': now_iso,
                })
            apply_id = result.get('data')

            log.info(f"不限时申请已提交: id={apply_id} user={user_id} "
                     f"material={material_id} duration={duration}min")
            return {"code": 0, "msg": "申请已提交，等待管理员审批", "data": {"success": True, "id": apply_id, "replaced": False}}
        except Exception as e:
            log.error(f"不限时申请提交失败: user={user_id} material={material_id}, {e}")
            return {"code": -1, "msg": f"申请失败: {str(e)}"}

    def list_unlimit_applications(self,
                                  status: Optional[str] = None,
                                  expires_at: Optional[str] = None) -> Dict[str, Any]:
        """列出不限时申请。

        Args:
            status: 过滤状态，逗号分隔（如 'pending,approved'），None 返回所有
            expires_at: 过期时间过滤，只返回 expires_at 大于此时间的记录（含 null），不传则不筛选
        """
        try:
            conditions: Dict[str, Any] = {}
            if status:
                conditions['status'] = {'in': status.split(',')}
            if expires_at:
                conditions['expires_at'] = {'>': expires_at}

            result = db_mgr.get_list(TABLE_UNLIMIT, page_size=1000, conditions=conditions)
            if result.get('code') != 0:
                return _err(f"查询失败: {result.get('msg')}", {})
            apps = result.get('data', {}).get('data', [])
            return {"code": 0, "msg": "ok", "data": {"applications": apps, "total": len(apps)}}
        except Exception as e:
            log.error(f"列出不限时申请失败: {e}")
            return {"code": -1, "msg": f"查询失败: {str(e)}"}

    def approve_unlimit(self, ids: List[int]) -> Dict[str, Any]:
        """批量审批通过不限时申请。"""
        try:
            approved_count = 0
            not_found_ids: List[int] = []

            for apply_id in ids:
                record = db_mgr.get_data(TABLE_UNLIMIT, apply_id, '*')
                if record.get('code') != 0 or not record.get('data'):
                    not_found_ids.append(apply_id)
                    continue
                data = record['data']
                if data.get('status') != 'pending':
                    not_found_ids.append(apply_id)
                    continue

                now_iso = _ts()
                duration_min = data.get('duration', 60)
                expires_at = _ts(duration_min)

                db_mgr.set_data(TABLE_UNLIMIT, {
                    'id': apply_id,
                    'status': 'approved',
                    'approved_at': now_iso,
                    'expires_at': expires_at,
                })

                approved_count += 1

            log.info(f"不限时审批通过: ids={ids} approved={approved_count} not_found={not_found_ids}")
            return {"code": 0, "msg": "ok", "data": {"approved": approved_count, "not_found": not_found_ids}}
        except Exception as e:
            log.error(f"不限时审批失败: {e}")
            return {"code": -1, "msg": f"审批失败: {str(e)}"}

    def deny_unlimit(self, ids: List[int]) -> Dict[str, Any]:
        """批量拒绝不限时申请。"""
        try:
            denied_count = 0
            not_found_ids: List[int] = []

            for apply_id in ids:
                record = db_mgr.get_data(TABLE_UNLIMIT, apply_id, '*')
                if record.get('code') != 0 or not record.get('data'):
                    not_found_ids.append(apply_id)
                    continue
                data = record['data']
                if data.get('status') != 'pending':
                    not_found_ids.append(apply_id)
                    continue

                db_mgr.set_data(TABLE_UNLIMIT, {
                    'id': apply_id,
                    'status': 'denied',
                    'denied_at': _ts(),
                })
                denied_count += 1

            log.info(f"不限时申请已拒绝: ids={ids} denied={denied_count} not_found={not_found_ids}")
            return {"code": 0, "msg": "ok", "data": {"denied": denied_count, "not_found": not_found_ids}}
        except Exception as e:
            log.error(f"不限时拒绝失败: {e}")
            return {"code": -1, "msg": f"拒绝失败: {str(e)}"}


material_mgr = MaterialMgr()
