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

