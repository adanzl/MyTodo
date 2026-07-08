"""任务管理路由 - 素材管理。
提供素材的增删改查功能。
"""

from __future__ import annotations

from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from pydantic import BaseModel

from core.config import app_logger
from core.services.task.task_mgr import task_mgr
from core.tools.validation import parse_with_model
from core.utils import _err, read_json_from_request
from typing import List

log = app_logger
task_bp = Blueprint('task', __name__)


class CalendarQuery(BaseModel):
    """任务日历查询参数"""
    date: str
    user_id: int | None = None


class FinishMaterialQuery(BaseModel):
    """完成素材打卡参数"""
    task_id: int
    material_id: int
    date: str
    user_id: int


class ApplyUnlimitQuery(BaseModel):
    """申请不限时参数"""
    user_id: int
    material_id: int
    task_id: int | None = None
    duration_hours: float = 1.0


class ApproveDenyQuery(BaseModel):
    """批量审批/拒绝参数"""
    ids: List[int]


@task_bp.route('/task/calendar', methods=['POST'])
def get_calendar() -> ResponseReturnValue:
    """查询任务日历，返回当月每天的任务素材完成情况"""
    json_data = read_json_from_request()
    body, err = parse_with_model(CalendarQuery, json_data, err_factory=_err)
    if err or not body:
        return err or _err('Invalid request body')

    result = task_mgr.get_task_calendar(body.date, body.user_id)
    return result


@task_bp.route('/task/finish', methods=['POST'])
def finish_material() -> ResponseReturnValue:
    """完成素材打卡"""
    json_data = read_json_from_request()
    body, err = parse_with_model(FinishMaterialQuery, json_data, err_factory=_err)
    if err or not body:
        return err or _err('Invalid request body')

    log.info(f"=> [Task Finish] {json_data}")
    result = task_mgr.finish_material(body.task_id, body.material_id, body.date, body.user_id)
    return result


@task_bp.route('/material/category/delete', methods=['POST'])
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

    result = task_mgr.delete_material_category(category_id, delete_materials)
    return result


@task_bp.route('/task/list', methods=['GET'])
def get_task_list() -> ResponseReturnValue:
    """获取任务列表（带锁定状态检查）"""
    user_id = request.args.get('userId', type=int)
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')
    page_num = request.args.get('pageNum', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)

    return task_mgr.get_task_list(user_id, start_date, end_date, page_num, page_size)


@task_bp.route('/task/update', methods=['POST'])
def update_task() -> ResponseReturnValue:
    """新增/更新任务（写路径规范化 end_date/rest_days）"""
    json_data = read_json_from_request()
    if not isinstance(json_data, dict):
        return _err('Invalid request body')
    result = task_mgr.update_task(json_data)
    return result


@task_bp.route('/material/status', methods=['GET'])
def get_material_status() -> ResponseReturnValue:
    """查询素材锁定状态（视频观看时长是否超限 + 白名单实时检查）"""
    user_id = request.args.get('userId', type=int)
    material_id = request.args.get('materialId', type=int)
    task_id = request.args.get('taskId', type=int)  # 可选，用于任务级白名单检查
    if not user_id or not material_id:
        return _err('Invalid userId or materialId')
    return task_mgr.get_material_status(user_id, material_id, task_id)


@task_bp.route('/material/unlimit/apply', methods=['POST'])
def apply_material_unlimit() -> ResponseReturnValue:
    """申请视频不限时（暂时解除观看时长限制）"""
    json_data = read_json_from_request()
    body, err = parse_with_model(ApplyUnlimitQuery, json_data, err_factory=_err)
    if err or not body:
        return err or _err('Invalid request body')

    log.info(f"=> [Unlimit Apply] user={body.user_id} material={body.material_id} duration={body.duration_hours}h")
    result = task_mgr.apply_unlimit(
        user_id=body.user_id,
        material_id=body.material_id,
        task_id=body.task_id,
        duration_hours=body.duration_hours,
    )
    return result


@task_bp.route('/material/unlimit/list', methods=['GET'])
def list_unlimit_applications() -> ResponseReturnValue:
    """列出所有未处理的不限时申请"""
    status = request.args.get('status', 'pending')
    return task_mgr.list_unlimit_applications(status if status else None)


@task_bp.route('/material/unlimit/approve', methods=['POST'])
def approve_unlimit_applications() -> ResponseReturnValue:
    """批量审批通过不限时申请"""
    json_data = read_json_from_request()
    body, err = parse_with_model(ApproveDenyQuery, json_data, err_factory=_err)
    if err or not body:
        return err or _err('Invalid request body')

    log.info(f"=> [Unlimit Approve] ids={body.ids}")
    result = task_mgr.approve_unlimit(body.ids)
    return result


@task_bp.route('/material/unlimit/deny', methods=['POST'])
def deny_unlimit_applications() -> ResponseReturnValue:
    """批量拒绝不限时申请"""
    json_data = read_json_from_request()
    body, err = parse_with_model(ApproveDenyQuery, json_data, err_factory=_err)
    if err or not body:
        return err or _err('Invalid request body')

    log.info(f"=> [Unlimit Deny] ids={body.ids}")
    result = task_mgr.deny_unlimit(body.ids)
    return result


@task_bp.route('/task/parent', methods=['GET'])
def get_material_parent_chain() -> ResponseReturnValue:
    """获取素材的父目录链"""
    material_id = request.args.get('materialId', type=int)
    if not material_id:
        return _err('Invalid materialId')
    
    result = task_mgr.get_material_parent_chain(material_id)
    return result
