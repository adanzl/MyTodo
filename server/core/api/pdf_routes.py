"""PDF 管理路由。
提供 PDF 文件上传、解密、列表、下载等功能。
"""

from __future__ import annotations

import os
from typing import Any, Dict

from flask import Blueprint, request, send_file
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from core.config import PDF_UNLOCK_DIR, PDF_UPLOAD_DIR, app_logger
from core.services.pdf_mgr import pdf_mgr
from core.utils import _err, _ok, read_json_from_request

log = app_logger
pdf_bp = Blueprint('pdf', __name__)


@pdf_bp.route("/pdf/upload", methods=['POST'])
def pdf_upload() -> ResponseReturnValue:
    """上传 PDF 文件。"""
    try:
        if 'file' not in request.files:
            return _err("未找到上传的文件")

        file = request.files['file']
        if file.filename == '':
            return _err("文件名不能为空")

        code, msg, file_info = pdf_mgr.upload_file(file, file.filename)
        if code != 0:
            return _err(msg)

        return _ok(file_info)

    except RequestEntityTooLarge:
        log.error("[PDF] 上传文件失败: 文件太大，超过服务器限制（最大 2000MB）")
        return _err("文件太大，超过服务器限制（最大 2000MB）")
    except Exception as e:
        log.error(f"[PDF] 上传文件失败: {e}")
        return _err(f"上传文件失败: {str(e)}")


@pdf_bp.route("/pdf/decrypt", methods=['POST'])
def pdf_decrypt() -> ResponseReturnValue:
    """解密 PDF 文件（异步处理）。"""
    try:
        data: Dict[str, Any] = read_json_from_request()
        task_id = data.get('task_id')
        password = data.get('password')

        if not task_id:
            return _err("任务ID不能为空")

        code, msg = pdf_mgr.decrypt(task_id, password)
        if code != 0:
            return _err(msg)

        return _ok({"message": msg})

    except Exception as e:
        log.error(f"[PDF] 提交解密任务失败: {e}")
        return _err(f"提交解密任务失败: {str(e)}")


@pdf_bp.route("/pdf/task/<path:task_id>", methods=['GET'])
def pdf_task_status(task_id: str) -> ResponseReturnValue:
    """获取 PDF 任务状态。"""
    try:
        code, msg, task_info = pdf_mgr.get_task_status(task_id)
        if code != 0:
            return _err(msg)

        return _ok(task_info)

    except Exception as e:
        log.error(f"[PDF] 获取任务状态失败: {e}")
        return _err(f"获取任务状态失败: {str(e)}")


@pdf_bp.route("/pdf/list", methods=['GET'])
def pdf_list() -> ResponseReturnValue:
    """列出 PDF 文件（上传/解密），并建立对应关系。"""
    try:
        result = pdf_mgr.list()
        return _ok(result)

    except Exception as e:
        log.error(f"[PDF] 列出文件失败: {e}")
        return _err(f"列出文件失败: {str(e)}")


@pdf_bp.route("/pdf/download/<path:filename>", methods=['GET'])
def pdf_download(filename: str) -> ResponseReturnValue:
    """下载 PDF 文件。"""
    try:
        file_type = request.args.get('type', 'unlocked')

        if file_type == 'uploaded':
            file_path = os.path.join(PDF_UPLOAD_DIR, secure_filename(filename))
        elif file_type == 'unlocked':
            file_path = os.path.join(PDF_UNLOCK_DIR, secure_filename(filename))
        else:
            return _err("无效的文件类型")

        if not os.path.exists(file_path):
            return _err("文件不存在")

        return send_file(file_path, as_attachment=True, download_name=filename)

    except Exception as e:
        log.error(f"[PDF] 下载文件失败: {e}")
        return _err(f"下载文件失败: {str(e)}")


@pdf_bp.route("/pdf/delete", methods=['POST'])
def pdf_delete() -> ResponseReturnValue:
    """删除 PDF 任务。"""
    try:
        data: Dict[str, Any] = read_json_from_request()
        task_id = data.get('task_id')

        if not task_id:
            return _err("任务ID不能为空")

        code, msg = pdf_mgr.delete(task_id)
        if code != 0:
            return _err(msg)

        return _ok({"message": msg})

    except Exception as e:
        log.error(f"[PDF] 删除任务失败: {e}")
        return _err(f"删除任务失败: {str(e)}")
