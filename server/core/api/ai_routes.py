"""AI routes.

提供 AI 相关功能的 API 接口：
- OCR 图片文字识别

所有路由挂载在 `/api` 下（由 create_app 设置 url_prefix='/'）。
"""

from __future__ import annotations

import os
import tempfile

from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from pydantic import BaseModel
from werkzeug.utils import secure_filename

from core.ai.ocr_ali import OCRAli
from core.config import app_logger
from core.tools.validation import parse_with_model
from core.utils import _err, _ok, read_json_from_request

log = app_logger

ai_bp = Blueprint('ai', __name__)

# 初始化 OCR 客户端
ocr_client = OCRAli()


class _OCRBody(BaseModel):
    """OCR 请求体（使用文件路径）"""
    image_paths: str | list[str]


@ai_bp.route('/ai/ocr', methods=['POST'])
def ocr() -> ResponseReturnValue:
    """OCR 图片文字识别接口。
    
    支持两种方式：
    1. 文件上传：通过 multipart/form-data 上传图片文件（支持多文件）
    2. JSON 请求：通过 JSON 传递图片路径（本地路径）
    
    Request (multipart/form-data):
        - files: 图片文件（支持多个，字段名可以是 'file' 或 'files[]'）
    
    Request (application/json):
        {
            "image_paths": "path/to/image.jpg"  // 单张图片
            或
            "image_paths": ["path/to/image1.jpg", "path/to/image2.jpg"]  // 多张图片
        }
    
    Returns:
        ResponseReturnValue: 
            - 成功: {"code": 0, "msg": "ok", "data": {"text": "识别的文本内容"}}
            - 失败: {"code": -1, "msg": "错误信息"}
    """
    try:
        image_paths = []
        temp_dir = None
        temp_paths = []
        is_uploaded = False
        
        # 方式1: 文件上传（multipart/form-data）
        if request.files:
            files = request.files.getlist('file') or request.files.getlist('files[]')
            
            if not files or all(f.filename == '' for f in files):
                return _err("未找到上传的图片文件")
            
            # 保存上传的文件到临时目录
            temp_dir = tempfile.mkdtemp(prefix='ocr_')
            temp_paths = []
            is_uploaded = True
            
            try:
                for file in files:
                    if file.filename == '':
                        continue
                    
                    # 使用安全文件名
                    safe_filename = secure_filename(file.filename)
                    temp_path = os.path.join(temp_dir, safe_filename)
                    file.save(temp_path)
                    temp_paths.append(temp_path)
                
                if not temp_paths:
                    # 清理临时目录
                    try:
                        os.rmdir(temp_dir)
                    except Exception:
                        pass
                    return _err("没有有效的图片文件")
                
                image_paths = temp_paths
                
            except Exception as e:
                # 清理临时文件
                for path in temp_paths:
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except Exception:
                        pass
                try:
                    if temp_dir and os.path.exists(temp_dir):
                        os.rmdir(temp_dir)
                except Exception:
                    pass
                log.error(f"[OCR] 保存上传文件失败: {e}")
                return _err(f"保存上传文件失败: {str(e)}")
        
        # 方式2: JSON 请求（使用本地路径）
        else:
            json_data = read_json_from_request()
            body, err = parse_with_model(_OCRBody, json_data, err_factory=_err)
            if err:
                return err
            
            # 统一转换为列表
            if isinstance(body.image_paths, str):
                image_paths = [body.image_paths]
            else:
                image_paths = body.image_paths
            
            # 验证文件是否存在
            for path in image_paths:
                if not os.path.exists(path):
                    return _err(f"图片文件不存在: {path}")
        
        if not image_paths:
            return _err("图片路径列表为空")
        
        # 调用 OCR 服务
        status, result = ocr_client.query(image_paths)
        
        # 清理临时文件（如果是上传的文件）
        if is_uploaded and temp_dir:
            try:
                for path in temp_paths:
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except Exception:
                        pass
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                log.warning(f"[OCR] 清理临时文件失败: {e}")
        
        if status == "error":
            return _err(result or "OCR 识别失败")
        
        return _ok({"text": result})
        
    except Exception as e:
        log.error(f"[OCR] OCR 接口错误: {e}")
        return _err(f"OCR 识别失败: {str(e)}")
