"""
PDF 管理路由
提供 PDF 文件上传、解密、列表等功能
"""
import os
from flask import Blueprint, request, send_file
from werkzeug.utils import secure_filename

from core.log_config import root_logger
from core.services.pdf_mgr import pdf_mgr
from core.utils import _ok, _err, read_json_from_request
from core.models.const import PDF_UPLOAD_DIR, PDF_UNLOCK_DIR

log = root_logger()
pdf_bp = Blueprint('pdf', __name__)


@pdf_bp.route("/pdf/upload", methods=['POST'])
def pdf_upload():
    """
    上传 PDF 文件
    """
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

    except Exception as e:
        log.error(f"[PDF] 上传文件失败: {e}")
        return _err(f"上传文件失败: {str(e)}")


@pdf_bp.route("/pdf/decrypt", methods=['POST'])
def pdf_decrypt():
    """
    解密 PDF 文件（异步处理）
    参数：
    - task_id: 任务ID（文件名）
    - password: 密码（可选，如果 PDF 需要密码）
    """
    try:
        data = read_json_from_request()
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
def pdf_task_status(task_id):
    """
    获取 PDF 任务状态
    参数：
    - task_id: 任务ID（文件名）
    """
    try:
        code, msg, task_info = pdf_mgr.get_task_status(task_id)
        if code != 0:
            return _err(msg)

        return _ok(task_info)

    except Exception as e:
        log.error(f"[PDF] 获取任务状态失败: {e}")
        return _err(f"获取任务状态失败: {str(e)}")


@pdf_bp.route("/pdf/list", methods=['GET'])
def pdf_list():
    """
    列出 PDF 文件
    返回上传的文件和已解密的文件，并建立对应关系
    """
    try:
        result = pdf_mgr.list()
        return _ok(result)

    except Exception as e:
        log.error(f"[PDF] 列出文件失败: {e}")
        return _err(f"列出文件失败: {str(e)}")


@pdf_bp.route("/pdf/download/<path:filename>", methods=['GET'])
def pdf_download(filename):
    """
    下载 PDF 文件
    参数：
    - filename: 文件名
    - type: 文件类型，'uploaded' 或 'unlocked'（默认 'unlocked'）
    """
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
def pdf_delete():
    """
    删除 PDF 任务
    参数：
    - task_id: 任务ID（文件名）
    """
    try:
        data = read_json_from_request()
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
