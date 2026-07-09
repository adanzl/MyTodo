"""素材管理服务。

提供素材锁定状态、不限时申请审批、分类管理等功能的业务逻辑。
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import current_app

from core.config import app_logger
from core.config.const import DEFAULT_BASE_DIR
from core.db.db_mgr import db_mgr
from core.db import rds_mgr
from core.tools.async_util import run_in_background
from core.utils import get_media_duration, validate_and_normalize_path
from .block_time import is_global_block_time_now, parse_block_time_config, _get_user_entry, _is_blocked_by_entry

log = app_logger

TABLE_MATERIAL = 't_material'
TABLE_TASK = 't_task'
TABLE_MATERIAL_CATEGORY = 't_material_category'

_ok = lambda data: {"code": 0, "msg": "ok", "data": data}
_err = lambda msg, data: {"code": -1, "msg": msg, "data": data}

PENDING_INDEX_KEY = "task:unlimit:apply:pending"

_unlimit_rds_key = lambda user_id: f"task:unlimit:{user_id}"


def _get_active_unlimit(user_id: int) -> Optional[Dict[str, Any]]:
    """检查用户是否存在有效的不限时记录。"""
    key = _unlimit_rds_key(user_id)
    raw = rds_mgr.get_str(key)
    if not raw:
        return None
    try:
        record = json.loads(raw)
        expiry_ts = record.get('expiry_ts', 0)
        if time.time() >= expiry_ts:
            return None
        return record
    except (json.JSONDecodeError, KeyError):
        return None


class MaterialMgr:
    """素材管理器"""

    LOCK_CODE_NONE = 0  # 未锁定
    LOCK_CODE_TASK_BLOCK = 1  # 任务级禁用时段
    LOCK_CODE_GLOBAL_BLOCK = 2  # 全局禁用时段
    LOCK_CODE_DURATION = 3  # 视频观看时长超限

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
            active_unlimit = _get_active_unlimit(user_id)
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
        task_id: Optional[int] = None,
        duration_hours: float = 1.0,
        lock_code: int = 0,
    ) -> Dict[str, Any]:
        """提交不限时申请（需管理员审批后生效）。

        Args:
            user_id: 用户ID
            material_id: 素材ID（记录用途）
            task_id: 任务ID（可选，记录用途）
            duration_hours: 申请不限时时长（小时）
            lock_code: 锁定类型码（0=未锁定, 1=任务禁用, 2=全局禁用, 3=时长超限）
        """
        try:
            apply_id = int(time.time() * 1000)
            now_iso = datetime.now().isoformat()
            record = {
                'id': apply_id,
                'user_id': user_id,
                'material_id': material_id,
                'task_id': task_id,
                'duration_hours': duration_hours,
                'lock_code': lock_code,
                'status': 'pending',
                'created_at': now_iso,
            }
            apply_key = f"task:unlimit:apply:{apply_id}"
            rds_mgr.set(apply_key, json.dumps(record, ensure_ascii=False))

            # 原子操作：移除旧申请 + 添加新申请
            replaced_id = None
            raw = rds_mgr.get_str(PENDING_INDEX_KEY)
            pending: List[Dict[str, Any]] = json.loads(raw) if raw else []
            new_pending: List[Dict[str, Any]] = []
            for item in pending:
                if item.get('user_id') == user_id and item.get('status') == 'pending':
                    replaced_id = item.get('id')
                    old_key = f"task:unlimit:apply:{replaced_id}"
                    old_raw = rds_mgr.get_str(old_key)
                    if old_raw:
                        old_record = json.loads(old_raw)
                        old_record['status'] = 'replaced'
                        old_record['replaced_at'] = now_iso
                        rds_mgr.set(old_key, json.dumps(old_record, ensure_ascii=False))
                else:
                    new_pending.append(item)
            new_pending.append({
                'id': apply_id,
                'user_id': user_id,
                'material_id': material_id,
                'task_id': task_id,
                'duration_hours': duration_hours,
                'lock_code': lock_code,
                'status': 'pending',
                'created_at': now_iso,
            })
            rds_mgr.set(PENDING_INDEX_KEY, json.dumps(new_pending, ensure_ascii=False))

            log.info(f"不限时申请已提交: id={apply_id} user={user_id} "
                     f"material={material_id} duration={duration_hours}h" +
                     (f" (替换旧申请 id={replaced_id})" if replaced_id else ""))
            msg = "申请已更新，等待管理员审批" if replaced_id else "申请已提交，等待管理员审批"
            return {"code": 0, "msg": msg, "data": {"success": True, "id": apply_id, "replaced": bool(replaced_id)}}
        except Exception as e:
            log.error(f"不限时申请提交失败: user={user_id} material={material_id}, {e}")
            return {"code": -1, "msg": f"申请失败: {str(e)}"}

    def list_unlimit_applications(self, status: Optional[str] = None) -> Dict[str, Any]:
        """列出不限时申请（默认只返回待审批的，每用户仅返回最新一条）。

        Args:
            status: 过滤状态，None 或 'pending' 返回待审批
        """
        try:
            raw = rds_mgr.get_str(PENDING_INDEX_KEY)
            all_apps: List[Dict[str, Any]] = json.loads(raw) if raw else []
            if status:
                all_apps = [a for a in all_apps if a.get('status') == status]
            else:
                all_apps = [a for a in all_apps if a.get('status') == 'pending']
            # 每用户仅返回最新一条
            seen: Dict[int, Dict[str, Any]] = {}
            for app in all_apps:
                uid = app.get('user_id')
                if uid is None:
                    continue
                existing = seen.get(uid)
                if not existing or app.get('id', 0) > existing.get('id', 0):
                    seen[uid] = app
            deduped = list(seen.values())
            return {"code": 0, "msg": "ok", "data": {"applications": deduped, "total": len(deduped)}}
        except Exception as e:
            log.error(f"列出不限时申请失败: {e}")
            return {"code": -1, "msg": f"查询失败: {str(e)}"}

    def approve_unlimit(self, ids: List[int]) -> Dict[str, Any]:
        """批量审批通过不限时申请。"""
        try:
            raw = rds_mgr.get_str(PENDING_INDEX_KEY)
            pending: List[Dict[str, Any]] = json.loads(raw) if raw else []
            approved_count = 0
            not_found_ids: List[int] = []

            for apply_id in ids:
                found = False
                for item in pending:
                    if item.get('id') == apply_id and item.get('status') == 'pending':
                        found = True
                        apply_key = f"task:unlimit:apply:{apply_id}"
                        apply_raw = rds_mgr.get_str(apply_key)
                        if apply_raw:
                            record = json.loads(apply_raw)
                            record['status'] = 'approved'
                            record['approved_at'] = datetime.now().isoformat()
                            rds_mgr.set(apply_key, json.dumps(record, ensure_ascii=False))

                            # 设置活跃不限时状态
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
                            unlimit_key = _unlimit_rds_key(record['user_id'])
                            rds_mgr.set(unlimit_key, json.dumps(unlimit_record, ensure_ascii=False))

                        item['status'] = 'approved'
                        item['approved_at'] = datetime.now().isoformat()
                        approved_count += 1
                        break

                if not found:
                    not_found_ids.append(apply_id)

            rds_mgr.set(PENDING_INDEX_KEY, json.dumps(pending, ensure_ascii=False))
            log.info(f"不限时审批通过: ids={ids} approved={approved_count} not_found={not_found_ids}")
            return {"code": 0, "msg": "ok", "data": {"approved": approved_count, "not_found": not_found_ids}}
        except Exception as e:
            log.error(f"不限时审批失败: {e}")
            return {"code": -1, "msg": f"审批失败: {str(e)}"}

    def deny_unlimit(self, ids: List[int]) -> Dict[str, Any]:
        """批量拒绝不限时申请。"""
        try:
            raw = rds_mgr.get_str(PENDING_INDEX_KEY)
            pending: List[Dict[str, Any]] = json.loads(raw) if raw else []
            denied_count = 0
            not_found_ids: List[int] = []

            for apply_id in ids:
                found = False
                for item in pending:
                    if item.get('id') == apply_id and item.get('status') == 'pending':
                        found = True
                        apply_key = f"task:unlimit:apply:{apply_id}"
                        apply_raw = rds_mgr.get_str(apply_key)
                        if apply_raw:
                            record = json.loads(apply_raw)
                            record['status'] = 'denied'
                            record['denied_at'] = datetime.now().isoformat()
                            rds_mgr.set(apply_key, json.dumps(record, ensure_ascii=False))

                        item['status'] = 'denied'
                        item['denied_at'] = datetime.now().isoformat()
                        denied_count += 1
                        break

                if not found:
                    not_found_ids.append(apply_id)

            rds_mgr.set(PENDING_INDEX_KEY, json.dumps(pending, ensure_ascii=False))
            log.info(f"不限时申请已拒绝: ids={ids} denied={denied_count} not_found={not_found_ids}")
            return {"code": 0, "msg": "ok", "data": {"denied": denied_count, "not_found": not_found_ids}}
        except Exception as e:
            log.error(f"不限时拒绝失败: {e}")
            return {"code": -1, "msg": f"拒绝失败: {str(e)}"}


material_mgr = MaterialMgr()
