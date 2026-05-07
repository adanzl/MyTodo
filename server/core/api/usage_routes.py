"""Usage 使用记录路由。
提供使用记录的添加、查询和删除功能。
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from pydantic import BaseModel

from core.config import app_logger
from core.services.usage_mgr import usage_mgr
from core.tools.validation import parse_with_model
from core.utils import _err, _ok, read_json_from_request

log = app_logger
usage_bp = Blueprint('usage', __name__)


class AddUsageQuery(BaseModel):
    """添加使用记录参数"""
    type: str
    start_time: str
    duration: int
    user_id: int
    out_key: int | None = None


class GetUsageListQuery(BaseModel):
    """获取使用记录列表参数"""
    page_num: int = 1
    page_size: int = 20
    user_id: int | None = None
    type: str | None = None


class DeleteUsageQuery(BaseModel):
    """删除使用记录参数"""
    id: int


class QuerySumQuery(BaseModel):
    """查询使用总时长参数"""
    user_id: int | None = None
    type: str | None = None
    time_start: str | None = None
    time_end: str | None = None


@usage_bp.route('/usage/add', methods=['POST'])
def add_usage() -> ResponseReturnValue:
    """添加使用记录"""
    json_data = read_json_from_request()
    body, err = parse_with_model(AddUsageQuery, json_data, err_factory=_err)
    if err or not body:
        return err or _err('Invalid request body')

    result = usage_mgr.add_usage(
        type=body.type,
        start_time=body.start_time,
        duration=body.duration,
        user_id=body.user_id,
        out_key=body.out_key,
    )
    return result


@usage_bp.route('/usage/list', methods=['POST'])
def get_usage_list() -> ResponseReturnValue:
    """获取使用记录列表"""
    json_data = read_json_from_request()
    body, err = parse_with_model(GetUsageListQuery, json_data, err_factory=_err)
    if err or not body:
        return err or _err('Invalid request body')

    result = usage_mgr.get_usage_list(
        page_num=body.page_num,
        page_size=body.page_size,
        user_id=body.user_id,
        type=body.type,
    )
    return result


@usage_bp.route('/usage/delete', methods=['POST'])
def delete_usage() -> ResponseReturnValue:
    """删除使用记录"""
    json_data = read_json_from_request()
    body, err = parse_with_model(DeleteUsageQuery, json_data, err_factory=_err)
    if err or not body:
        return err or _err('Invalid request body')

    result = usage_mgr.delete_usage(id=body.id)
    return result


@usage_bp.route('/usage/querySum', methods=['GET'])
def query_sum_usage() -> ResponseReturnValue:
    """查询使用总时长"""
    try:
        user_id = request.args.get('user_id', type=int)
        type_param = request.args.get('type', type=str)
        time_start = request.args.get('time_start', type=str)
        time_end = request.args.get('time_end', type=str)

        result = usage_mgr.query_sum_usage(
            user_id=user_id,
            type=type_param,
            time_start=time_start,
            time_end=time_end,
        )
        return result
    except Exception as e:
        log.error(f"[UsageRoutes] 查询总时长异常: {e}", exc_info=True)
        return _err(f'error: {str(e)}')
