"""图片相关 API 路由模块。

路径统一以 /pic/ 为前缀。上传的图片保存在 DEFAULT_BASE_DIR/pic 目录下。
"""

from __future__ import annotations

import os
from typing import Any, Optional

from flask import Blueprint, jsonify, render_template, request, send_file
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from core.config import PIC_BASE_DIR, app_logger
from core.db.db_mgr import db_mgr
from core.utils import _err, _ok, ensure_directory, get_unique_filepath, is_allowed_image_file

log = app_logger
pic_bp = Blueprint('pic', __name__)


def _parse_int(
        value: Any,
        name: str) -> tuple[Optional[int], Optional[ResponseReturnValue]]:
    """把输入解析为 int。失败时返回错误响应。"""
    if value is None or value == "":
        return None, {"code": -1, "msg": f"{name} is required"}
    try:
        return int(value), None
    except (TypeError, ValueError):
        return None, {"code": -1, "msg": f"{name} must be int"}


def _safe_pic_path(filename: str) -> tuple[Optional[str], Optional[str]]:
    """校验文件名并返回安全路径。返回 (abs_path, error_msg)。"""
    if not filename:
        return None, "文件名为空"
    safe_name = secure_filename(filename)
    if not safe_name:
        return None, "非法文件名"
    if not is_allowed_image_file(safe_name):
        return None, "不允许的图片格式，支持 jpg/jpeg/png/gif/webp/bmp"
    abs_path = os.path.abspath(os.path.join(PIC_BASE_DIR, safe_name))
    if not abs_path.startswith(os.path.abspath(PIC_BASE_DIR)):
        return None, "非法路径"
    return abs_path, None


# =========== 数据库图片（兼容旧接口）==========
@pic_bp.route("/viewPic", methods=['GET'])
def view_pic() -> ResponseReturnValue:
    """从数据库按 id 查看图片（base64 渲染）。"""
    raw_id = request.args.get('id')
    if raw_id is None:
        return jsonify({'error': 'id is required'}), 400

    log.info("===== [View Pic] " + raw_id)

    pic_id, err = _parse_int(raw_id, 'id')
    if err:
        return jsonify({'error': err.get('msg', 'invalid id')}), 400

    p_data = db_mgr.get_data_idx(db_mgr.TABLE_PIC, pic_id)
    if p_data['code'] == 0:
        return render_template('image.html', image_data=p_data['data'])
    else:
        return jsonify({'error': 'Image not found'}), 404


# =========== 文件系统图片（上传/删除/查看）==========
@pic_bp.route("/upload", methods=['POST'])
def upload() -> ResponseReturnValue:
    """上传图片到 DEFAULT_BASE_DIR/pic 目录。"""
    try:
        if 'file' not in request.files:
            return _err("未找到上传的文件")

        file = request.files['file']
        if file.filename == '':
            return _err("文件名不能为空")

        if not is_allowed_image_file(file.filename):
            return _err("不允许的图片格式，支持 jpg/jpeg/png/gif/webp/bmp")

        ensure_directory(PIC_BASE_DIR)
        base_name, ext = os.path.splitext(secure_filename(file.filename))
        base_name = base_name or "image"
        target_path = get_unique_filepath(PIC_BASE_DIR, base_name, ext.lower())
        file.save(target_path)
        filename = os.path.basename(target_path)
        log.info(f"[Pic] 上传成功: {filename}")
        return _ok({"filename": filename, "path": target_path})

    except RequestEntityTooLarge:
        log.error("[Pic] 上传失败: 文件太大")
        return _err("文件太大，超过服务器限制")
    except Exception as e:
        log.error(f"[Pic] 上传失败: {e}")
        return _err(f"上传失败: {str(e)}")


@pic_bp.route("/delete", methods=['POST'])
def delete() -> ResponseReturnValue:
    """删除指定文件名的图片。"""
    try:
        # 支持 JSON body 或 form
        data = request.get_json(silent=True) or {}
        name = data.get('name') or request.form.get('name') or request.args.get('name')
        if not name:
            return _err("缺少参数 name")

        abs_path, err_msg = _safe_pic_path(name)
        if err_msg:
            return _err(err_msg)
        if not os.path.isfile(abs_path):
            return _err("文件不存在")

        os.remove(abs_path)
        log.info(f"[Pic] 删除成功: {name}")
        return _ok({"filename": name})

    except Exception as e:
        log.error(f"[Pic] 删除失败: {e}")
        return _err(f"删除失败: {str(e)}")


@pic_bp.route("/view", methods=['GET'])
def view() -> ResponseReturnValue:
    """按文件名查看已上传的图片。"""
    name = request.args.get('name')
    if not name:
        return jsonify({'error': 'name is required'}), 400

    abs_path, err_msg = _safe_pic_path(name)
    if err_msg:
        return jsonify({'error': err_msg}), 400
    if not os.path.isfile(abs_path):
        return jsonify({'error': 'Image not found'}), 404

    return send_file(abs_path, mimetype=None, as_attachment=False)
