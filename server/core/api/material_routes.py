"""素材管理路由。

提供素材锁定状态、不限时申请审批等功能的 HTTP API。
"""

from __future__ import annotations

from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from pydantic import BaseModel
from typing import List

from core.config import app_logger
from core.services.task.material_mgr import material_mgr
from core.tools.validation import parse_with_model
from core.utils import _err, read_json_from_request

log = app_logger
material_bp = Blueprint('material', __name__)


class ApplyUnlimitQuery(BaseModel):
    """申请不限时参数"""
    user_id: int
    material_id: int
    task_id: int | None = None
    duration_hours: float = 1.0
    lock_code: int = 0


class ApproveDenyQuery(BaseModel):
    """批量审批/拒绝参数"""
    ids: List[int]


@material_bp.route('/material/category/delete', methods=['POST'])
def delete_material_category() -> ResponseReturnValue:
    """删除素材分类（文件夹）"""
    json_data = read_json_from_request()
    if not json_data or 'id' not in json_data:
        return _err('Invalid request body')

    category_id = json_data.get('id')
    if not isinstance(category_id, int):
        return _err('Invalid category id')

    log.info(f"=> [Task Delete Material Category] {json_data}")
    # 获取是否删除素材的参数，默认为 False
    delete_materials = json_data.get('deleteMaterials', False)
    if not isinstance(delete_materials, bool):
        return _err('Invalid deleteMaterials parameter')

    result = material_mgr.delete_material_category(category_id, delete_materials)
    return result


@material_bp.route('/material/status', methods=['GET'])
def get_material_status() -> ResponseReturnValue:
    """查询素材锁定状态（视频观看时长是否超限 + 白名单实时检查）"""
    user_id = request.args.get('userId', type=int)
    material_id = request.args.get('materialId', type=int)
    task_id = request.args.get('taskId', type=int)  # 可选，用于任务级白名单检查
    if not user_id or not material_id:
        return _err('Invalid userId or materialId')
    return material_mgr.get_material_status(user_id, material_id, task_id)


@material_bp.route('/material/unlimit/apply', methods=['POST'])
def apply_material_unlimit() -> ResponseReturnValue:
    """申请视频不限时（暂时解除观看时长限制）"""
    json_data = read_json_from_request()
    body, err = parse_with_model(ApplyUnlimitQuery, json_data, err_factory=_err)
    if err or not body:
        return err or _err('Invalid request body')

    log.info(f"=> [Unlimit Apply] user={body.user_id} material={body.material_id} duration={body.duration_hours}h")
    result = material_mgr.apply_unlimit(
        user_id=body.user_id,
        material_id=body.material_id,
        task_id=body.task_id,
        duration_hours=body.duration_hours,
        lock_code=body.lock_code,
    )
    return result


@material_bp.route('/material/unlimit/list', methods=['GET'])
def list_unlimit_applications() -> ResponseReturnValue:
    """列出所有未处理的不限时申请"""
    status = request.args.get('status', 'pending')
    return material_mgr.list_unlimit_applications(status if status else None)


@material_bp.route('/material/unlimit/approve', methods=['POST'])
def approve_unlimit_applications() -> ResponseReturnValue:
    """批量审批通过不限时申请"""
    json_data = read_json_from_request()
    body, err = parse_with_model(ApproveDenyQuery, json_data, err_factory=_err)
    if err or not body:
        return err or _err('Invalid request body')

    log.info(f"=> [Unlimit Approve] ids={body.ids}")
    result = material_mgr.approve_unlimit(body.ids)
    return result


@material_bp.route('/material/unlimit/deny', methods=['POST'])
def deny_unlimit_applications() -> ResponseReturnValue:
    """批量拒绝不限时申请"""
    json_data = read_json_from_request()
    body, err = parse_with_model(ApproveDenyQuery, json_data, err_factory=_err)
    if err or not body:
        return err or _err('Invalid request body')

    log.info(f"=> [Unlimit Deny] ids={body.ids}")
    result = material_mgr.deny_unlimit(body.ids)
    return result


@material_bp.route('/material/parent', methods=['GET'])
def get_material_parent_chain() -> ResponseReturnValue:
    """获取素材的父目录链"""
    material_id = request.args.get('materialId', type=int)
    if not material_id:
        return _err('Invalid materialId')

    result = material_mgr.get_material_parent_chain(material_id)
    return result
