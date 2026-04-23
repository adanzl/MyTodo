"""任务管理路由 - 素材管理。
提供素材的增删改查功能。
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from pydantic import BaseModel

from core.config import app_logger
from core.services.task_mgr import task_mgr
from core.tools.validation import parse_with_model
from core.utils import _err, _ok, read_json_from_request

log = app_logger
task_bp = Blueprint('task', __name__)


class CalendarQuery(BaseModel):
    """任务日历查询参数"""
    date: str
    user_id: int | None = None


@task_bp.route('/calendar', methods=['POST'])
def get_calendar() -> ResponseReturnValue:
    """查询任务日历，返回当月每天的任务素材完成情况"""
    json_data = read_json_from_request()
    body, err = parse_with_model(CalendarQuery, json_data, err_factory=_err)
    if err or not body :
        return err or _err('Invalid request body')

    result = task_mgr.get_task_calendar(body.date, body.user_id)
    return result
