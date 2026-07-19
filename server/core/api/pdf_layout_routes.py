"""PDF 排版管理路由。
提供 PDF 文件上传、排版处理、列表、下载等功能。
"""
from __future__ import annotations
from core import limiter

import os
from typing import Any, Dict

from flask import Blueprint, request, send_file
from flask.typing import ResponseReturnValue
from pydantic import BaseModel
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from core.config import PDF_LAYOUT_UPLOAD_DIR, PDF_LAYOUT_OUTPUT_DIR, app_logger
from core.services.tools.pdf_layout_mgr import pdf_layout_mgr
from core.tools.validation import parse_with_model
from core.utils import _err, _ok, read_json_from_request

log = app_logger
pdf_layout_bp = Blueprint('pdf_layout', __name__)


class _PdfLayoutProcessBody(BaseModel):
    task_id: str


class _PdfLayoutDeleteBody(BaseModel):
    task_id: str


class _PdfLayoutUpdateBody(BaseModel):
    task_id: str
    fill_configs: list[int]


@limiter.limit("10 per minute; 50 per hour")
@pdf_layout_bp.route("/pdf_layout/upload", methods=['POST'])
def pdf_layout_upload() -> ResponseReturnValue:
    """上传 PDF 文件。"""
    try:
        if 'file' not in request.files:
            return _err("未找到上传的文件")

        file = request.files['file']
        if not file.filename or file.filename == '':
            return _err("文件名不能为空")

        code, msg, task_id = pdf_layout_mgr.create_task(file, file.filename)
        if code != 0 or not task_id:
            return _err(msg)

        task_info = pdf_layout_mgr.get_task(task_id)
        if not task_info:
            return _err('任务创建成功但无法读取任务信息')

        return _ok(task_info)

    except RequestEntityTooLarge:
        log.error("[PDF 排版] 上传文件失败: 文件太大，超过服务器限制（最大 2000MB）")
        return _err("文件太大，超过服务器限制（最大 2000MB）")
    except Exception as e:
        log.error(f"[PDF 排版] 上传文件失败: {e}")
        return _err(f"上传文件失败: {str(e)}")


@limiter.limit("10 per minute; 50 per hour")
@pdf_layout_bp.route("/pdf_layout/process", methods=['POST'])
def pdf_layout_process() -> ResponseReturnValue:
    """排版处理 PDF 文件（异步处理）。"""
    try:
        data: Dict[str, Any] = read_json_from_request()
        body, err = parse_with_model(
            _PdfLayoutProcessBody, data, err_factory=_err)
        if err or not body:
            return err or _err("Invalid request body")

        code, msg = pdf_layout_mgr.start_task(body.task_id)
        if code != 0:
            return _err(msg)

        return _ok({"message": msg})

    except Exception as e:
        log.error(f"[PDF 排版] 提交排版任务失败: {e}")
        return _err(f"提交排版任务失败: {str(e)}")


@pdf_layout_bp.route("/pdf_layout/task/<path:task_id>", methods=['GET'])
def pdf_layout_task_status(task_id: str) -> ResponseReturnValue:
    """获取 PDF 排版任务状态。"""
    try:
        task_info = pdf_layout_mgr.get_task(task_id)
        if not task_info:
            return _err('任务不存在')

        return _ok(task_info)

    except Exception as e:
        log.error(f"[PDF 排版] 获取任务状态失败: {e}")
        return _err(f"获取任务状态失败: {str(e)}")


@pdf_layout_bp.route("/pdf_layout/list", methods=['GET'])
def pdf_layout_list() -> ResponseReturnValue:
    """列出 PDF 排版任务列表。"""
    try:
        result = pdf_layout_mgr.list_tasks()
        return _ok(result)

    except Exception as e:
        log.error(f"[PDF 排版] 列出任务失败: {e}")
        return _err(f"列出任务失败: {str(e)}")


@pdf_layout_bp.route("/pdf_layout/download/<path:filename>", methods=['GET'])
def pdf_layout_download(filename: str) -> ResponseReturnValue:
    """下载排版后的 PDF 文件。"""
    try:
        file_type = request.args.get('type', 'output')

        if file_type == 'uploaded':
            file_path = os.path.join(
                PDF_LAYOUT_UPLOAD_DIR, secure_filename(filename))
        elif file_type == 'output':
            file_path = os.path.join(
                PDF_LAYOUT_OUTPUT_DIR, secure_filename(filename))
        else:
            return _err("无效的文件类型")

        if not os.path.exists(file_path):
            return _err("文件不存在")

        return send_file(file_path, as_attachment=True, download_name=filename)

    except Exception as e:
        log.error(f"[PDF 排版] 下载文件失败: {e}")
        return _err(f"下载文件失败: {str(e)}")


@pdf_layout_bp.route("/pdf_layout/delete", methods=['POST'])
def pdf_layout_delete() -> ResponseReturnValue:
    """删除 PDF 排版任务。"""
    try:
        data: Dict[str, Any] = read_json_from_request()
        body, err = parse_with_model(
            _PdfLayoutDeleteBody, data, err_factory=_err)
        if err or not body:
            return err or _err("Invalid request body")

        code, msg = pdf_layout_mgr.delete_task(body.task_id)
        if code != 0:
            return _err(msg)

        return _ok({"message": msg})

    except Exception as e:
        log.error(f"[PDF 排版] 删除任务失败: {e}")
        return _err(f"删除任务失败: {str(e)}")


@pdf_layout_bp.route("/pdf_layout/save", methods=['POST'])
def pdf_layout_save() -> ResponseReturnValue:
    """生成骑缝排版 PDF。"""
    try:
        data: Dict[str, Any] = read_json_from_request()
        body, err = parse_with_model(
            _PdfLayoutUpdateBody, data, err_factory=_err)
        if err or not body:
            return err or _err("Invalid request body")

        code, msg = pdf_layout_mgr.save_layout(body.task_id, body.fill_configs)
        if code != 0:
            return _err(msg)

        task_info = pdf_layout_mgr.get_task(body.task_id)
        return _ok(task_info)

    except Exception as e:
        log.error(f"[PDF 排版] 保存骑缝 PDF 失败: {e}")
        return _err(f"保存骑缝 PDF 失败: {str(e)}")
