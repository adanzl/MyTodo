"""图片相关 API 路由模块。

路径统一以 /pic/ 为前缀。核心逻辑在 core.services.pic_mgr。
"""

from __future__ import annotations

from typing import Any, Optional

from flask import Blueprint, jsonify, render_template, request, send_file
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import RequestEntityTooLarge

from core.config import app_logger
from core.db.db_mgr import db_mgr
from core.services.pic_mgr import pic_mgr
from core.utils import _err, _ok

log = app_logger
pic_bp = Blueprint('pic', __name__)


def _parse_int(value: Any, name: str) -> tuple[Optional[int], Optional[str]]:
    """解析为 int。失败时返回 (None, error_msg)。"""
    if value is None or value == "":
        return None, f"{name} is required"
    try:
        v = int(value)
        return v, None
    except (TypeError, ValueError):
        return None, f"{name} must be int"


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
        return jsonify({'error': err}), 400

    p_data = db_mgr.get_data_idx(db_mgr.TABLE_PIC, pic_id)
    if p_data['code'] == 0:
        return render_template('image.html', image_data=p_data['data'])
    return jsonify({'error': 'Image not found'}), 404


# =========== 文件系统图片（上传/删除/查看）==========
@pic_bp.route("/upload", methods=['POST'])
def upload() -> ResponseReturnValue:
    """上传图片到 pic 目录。"""
    try:
        if 'file' not in request.files:
            return _err("未找到上传的文件")

        file = request.files['file']
        filename, target_path = pic_mgr.upload(file)
        return _ok({"filename": filename, "path": target_path})

    except RequestEntityTooLarge:
        log.error("[Pic] 上传失败: 文件太大")
        return _err("文件太大，超过服务器限制")
    except ValueError as e:
        return _err(str(e))
    except Exception as e:
        log.error(f"[Pic] 上传失败: {e}")
        return _err(f"上传失败: {str(e)}")


@pic_bp.route("/delete", methods=['POST'])
def delete() -> ResponseReturnValue:
    """删除指定文件名的图片及其所有缓存变体。"""
    try:
        data = request.get_json(silent=True) or {}
        name = data.get('name') or request.form.get('name') or request.args.get('name')
        if not name:
            return _err("缺少参数 name")

        deleted = pic_mgr.delete(name)
        return _ok({"deleted": deleted})

    except ValueError as e:
        return _err(str(e))
    except FileNotFoundError as e:
        return _err(str(e))
    except Exception as e:
        log.error(f"[Pic] 删除失败: {e}")
        return _err(f"删除失败: {str(e)}")


@pic_bp.route("/view", methods=['GET'])
def view() -> ResponseReturnValue:
    """按文件名查看图片。支持 w、h 参数按比例缩放并缓存。"""
    name = request.args.get('name')
    if not name:
        return jsonify({'error': 'name is required'}), 400

    w_raw = request.args.get('w')
    h_raw = request.args.get('h')

    # 解析 w、h
    w_val, h_val = None, None
    if w_raw is not None or h_raw is not None:
        w_val, err = _parse_int(w_raw or "0", 'w')
        h_val, err = _parse_int(h_raw or "0", 'h')
        if err or (w_val is not None and w_val <= 0) or (h_val is not None and h_val <= 0):
            return jsonify({'error': 'w 和 h 必须为正整数'}), 400

    try:
        path, mimetype = pic_mgr.get_view_path(name, w_val, h_val)
        return send_file(path, mimetype=mimetype, as_attachment=False)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        log.error(f"[Pic] 查看失败: {e}")
        return jsonify({'error': f'图片处理失败: {str(e)}'}), 500
