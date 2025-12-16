"""
PDF 管理路由
提供 PDF 文件上传、解密、列表等功能
"""
import os
import shutil
from flask import Blueprint, request, send_file
from werkzeug.utils import secure_filename

from core.log_config import root_logger
from core.services.pdf_mgr import decrypt_pdf
from core.utils import _ok, _err

log = root_logger()
pdf_bp = Blueprint('pdf', __name__)

# 常量定义
PDF_UPLOAD_DIR = '/tmp/my_todo/pdf'
PDF_UNLOCK_DIR = '/tmp/my_todo/pdf/unlock'

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'.pdf'}


def _ensure_directories():
    """确保必要的目录存在"""
    os.makedirs(PDF_UPLOAD_DIR, exist_ok=True)
    os.makedirs(PDF_UNLOCK_DIR, exist_ok=True)


def _allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


def _get_file_info(file_path: str) -> dict:
    """获取文件信息"""
    if not os.path.exists(file_path):
        return None
    
    stat_info = os.stat(file_path)
    return {
        "name": os.path.basename(file_path),
        "path": file_path,
        "size": stat_info.st_size,
        "modified": stat_info.st_mtime,
    }


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
        
        if not _allowed_file(file.filename):
            return _err("只支持 PDF 文件")
        
        # 确保目录存在
        _ensure_directories()
        
        # 使用安全文件名
        filename = secure_filename(file.filename)
        file_path = os.path.join(PDF_UPLOAD_DIR, filename)
        
        # 如果文件已存在，添加序号
        if os.path.exists(file_path):
            base_name, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(file_path):
                new_filename = f"{base_name}_{counter}{ext}"
                file_path = os.path.join(PDF_UPLOAD_DIR, new_filename)
                counter += 1
            filename = os.path.basename(file_path)
        
        # 保存文件
        file.save(file_path)
        log.info(f"[PDF] 文件上传成功: {file_path}")
        
        file_info = _get_file_info(file_path)
        return _ok(file_info)
        
    except Exception as e:
        log.error(f"[PDF] 上传文件失败: {e}")
        return _err(f"上传文件失败: {str(e)}")


@pdf_bp.route("/pdf/decrypt", methods=['POST'])
def pdf_decrypt():
    """
    解密 PDF 文件
    参数：
    - filename: 要解密的文件名（在 /tmp/my_todo/pdf 目录下）
    - password: 密码（可选，如果 PDF 需要密码）
    """
    try:
        data = request.get_json() or {}
        filename = data.get('filename')
        password = data.get('password')
        
        if not filename:
            return _err("文件名不能为空")
        
        # 确保目录存在
        _ensure_directories()
        
        # 构建文件路径
        input_path = os.path.join(PDF_UPLOAD_DIR, secure_filename(filename))
        
        if not os.path.exists(input_path):
            return _err(f"文件不存在: {filename}")
        
        # 构建输出文件路径
        base_name, ext = os.path.splitext(filename)
        output_filename = f"{base_name}_unlocked{ext}"
        output_path = os.path.join(PDF_UNLOCK_DIR, output_filename)
        
        # 如果输出文件已存在，删除它
        if os.path.exists(output_path):
            os.remove(output_path)
        
        # 执行解密
        code, msg = decrypt_pdf(input_path, output_path, password=password)
        
        if code != 0:
            return _err(msg)
        
        file_info = _get_file_info(output_path)
        log.info(f"[PDF] 文件解密成功: {output_path}")
        return _ok(file_info)
        
    except Exception as e:
        log.error(f"[PDF] 解密文件失败: {e}")
        return _err(f"解密文件失败: {str(e)}")


@pdf_bp.route("/pdf/list", methods=['GET'])
def pdf_list():
    """
    列出 PDF 文件
    返回上传的文件和已解密的文件，并建立对应关系
    """
    try:
        # 确保目录存在
        _ensure_directories()
        
        # 获取上传的文件列表
        uploaded_files = []
        if os.path.exists(PDF_UPLOAD_DIR):
            for filename in os.listdir(PDF_UPLOAD_DIR):
                file_path = os.path.join(PDF_UPLOAD_DIR, filename)
                if os.path.isfile(file_path) and _allowed_file(filename):
                    file_info = _get_file_info(file_path)
                    if file_info:
                        uploaded_files.append(file_info)
        
        # 获取已解密的文件列表
        unlocked_files = []
        if os.path.exists(PDF_UNLOCK_DIR):
            for filename in os.listdir(PDF_UNLOCK_DIR):
                file_path = os.path.join(PDF_UNLOCK_DIR, filename)
                if os.path.isfile(file_path) and _allowed_file(filename):
                    file_info = _get_file_info(file_path)
                    if file_info:
                        unlocked_files.append(file_info)
        
        # 建立文件对应关系
        # 已解密的文件名格式：原文件名_unlocked.pdf
        file_mapping = []
        for uploaded in uploaded_files:
            uploaded_name = uploaded['name']
            base_name, ext = os.path.splitext(uploaded_name)
            unlocked_name = f"{base_name}_unlocked{ext}"
            
            # 查找对应的已解密文件
            unlocked_file = None
            for unlocked in unlocked_files:
                if unlocked['name'] == unlocked_name:
                    unlocked_file = unlocked
                    break
            
            file_mapping.append({
                "uploaded": uploaded,
                "unlocked": unlocked_file,
                "has_unlocked": unlocked_file is not None
            })
        
        # 添加没有对应上传文件的已解密文件（可能是手动添加的）
        for unlocked in unlocked_files:
            unlocked_name = unlocked['name']
            if unlocked_name.endswith('_unlocked.pdf'):
                # 检查是否已经在映射中
                found = False
                for mapping in file_mapping:
                    if mapping['unlocked'] and mapping['unlocked']['name'] == unlocked_name:
                        found = True
                        break
                if not found:
                    file_mapping.append({
                        "uploaded": None,
                        "unlocked": unlocked,
                        "has_unlocked": True
                    })
        
        return _ok({
            "uploaded": uploaded_files,
            "unlocked": unlocked_files,
            "mapping": file_mapping
        })
        
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
    删除 PDF 文件
    参数：
    - filename: 文件名
    - type: 文件类型，'uploaded' 或 'unlocked' 或 'both'（默认 'both'）
    """
    try:
        data = request.get_json() or {}
        filename = data.get('filename')
        file_type = data.get('type', 'both')
        
        if not filename:
            return _err("文件名不能为空")
        
        deleted_files = []
        
        if file_type in ('uploaded', 'both'):
            uploaded_path = os.path.join(PDF_UPLOAD_DIR, secure_filename(filename))
            if os.path.exists(uploaded_path):
                os.remove(uploaded_path)
                deleted_files.append(uploaded_path)
                log.info(f"[PDF] 删除上传文件: {uploaded_path}")
        
        if file_type in ('unlocked', 'both'):
            # 删除对应的已解密文件
            base_name, ext = os.path.splitext(filename)
            unlocked_filename = f"{base_name}_unlocked{ext}"
            unlocked_path = os.path.join(PDF_UNLOCK_DIR, secure_filename(unlocked_filename))
            if os.path.exists(unlocked_path):
                os.remove(unlocked_path)
                deleted_files.append(unlocked_path)
                log.info(f"[PDF] 删除已解密文件: {unlocked_path}")
        
        if not deleted_files:
            return _err("文件不存在")
        
        return _ok({"deleted": deleted_files})
        
    except Exception as e:
        log.error(f"[PDF] 删除文件失败: {e}")
        return _err(f"删除文件失败: {str(e)}")

