"""通用 API 路由模块（api_bp）"""

from __future__ import annotations

import os
import random
import re
import urllib.parse
from typing import Any, Dict, Optional

import core.db.rds_mgr as rds_mgr
from core.ai.ai_local import AILocal
from core.config import app_logger
from core.config import config
from core.db.db_mgr import db_mgr
from core.utils import get_media_duration, read_json_from_request
from flask import Blueprint, json, jsonify, render_template, request
from flask.typing import ResponseReturnValue

log = app_logger
api_bp = Blueprint('api', __name__)


def _parse_int(value: Any, name: str) -> tuple[Optional[int], Optional[ResponseReturnValue]]:
    """把输入解析为 int。失败时返回错误响应。"""
    if value is None or value == "":
        return None, {"code": -1, "msg": f"{name} is required"}
    try:
        return int(value), None
    except (TypeError, ValueError):
        return None, {"code": -1, "msg": f"{name} must be int"}


@api_bp.route("/natapp")
def natapp() -> ResponseReturnValue:
    with open("/opt/natapp/logs/natapp_web.log", "r") as f:
        log_content = f.read()
        return f"""
            <html>
            <head>
                <title>Natapp Log</title>
            </head>
            <body>
                <pre>{log_content}</pre>
            </body>
            </html>
        """


@api_bp.route("/log")
def server_log() -> ResponseReturnValue:
    with open("logs/app.log", "r") as f:
        lines = f.readlines()
        lines.reverse()
        log_content = ''.join(lines)
    return render_template('server_log.html', log_content=log_content)


@api_bp.route("/write_log", methods=['POST'])
def write_log() -> ResponseReturnValue:
    try:
        args = request.get_data().decode('utf-8')
        log.info("===== [Write Log] " + args)
    except Exception as e:
        log.error(e)
    return {}


# =========== PIC ==========
@api_bp.route("/viewPic", methods=['GET'])
def view_pic() -> ResponseReturnValue:
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


# =========== SAVE ==========
@api_bp.route("/getSave", methods=['GET'])
def get_save() -> ResponseReturnValue:
    raw_id = request.args.get('id')
    log.info(f"===== [Get Save] id={raw_id}")

    save_id, err = _parse_int(raw_id, 'id')
    if err:
        return err

    return db_mgr.get_save(save_id)


@api_bp.route("/setSave", methods=['POST'])
def set_save() -> ResponseReturnValue:
    args: Dict[str, Any] = read_json_from_request()
    log.info("===== [Set Save] " + json.dumps(args))

    raw_id = args.get('id')
    save_id, err = _parse_int(raw_id, 'id')
    if err:
        return err

    user = args.get('user')
    data = json.dumps(args.get('data'))
    return db_mgr.set_save(save_id, user, data)


# =========== Common ==========
@api_bp.route("/getAll", methods=['GET'])
def get_all() -> ResponseReturnValue:
    page_size = request.args.get('pageSize', 20, type=int)
    page_num = request.args.get('pageNum', 1, type=int)
    fields = request.args.get('fields', '*')
    conditions_str = request.args.get('conditions')
    conditions = json.loads(conditions_str) if conditions_str else None
    table = request.args.get('table')
    # log.info("===== [Get All Data] " + json.dumps(request.args))
    if fields != '*':
        fields = fields.split(',')
    return db_mgr.get_list(table, page_num, page_size, fields, conditions)


@api_bp.route("/getData", methods=['GET'])
def get_data() -> ResponseReturnValue:
    table = request.args.get('table')
    raw_id = request.args.get('id')
    idx = request.args.get('idx', type=int)
    fields = request.args.get('fields')
    log.info("===== [Get Data] " + json.dumps(request.args))

    data_id, err = _parse_int(raw_id, 'id')
    if err:
        return err

    if fields is None:
        return db_mgr.get_data_idx(table, data_id, idx)
    else:
        return db_mgr.get_data(table, data_id, fields)


from core import limiter


@limiter.limit("10 per minute; 50 per hour")
@api_bp.route("/setData", methods=['POST'])
def set_data() -> ResponseReturnValue:
    args: Dict[str, Any] = read_json_from_request()
    table = args.get('table')
    data = args.get('data')
    log.info(f"===== [Set Data] {table}: {len(data) if hasattr(data, '__len__') else 0}")
    return db_mgr.set_data(table, data)


@api_bp.route("/delData", methods=['POST'])
def del_data() -> ResponseReturnValue:
    args: Dict[str, Any] = read_json_from_request()
    log.info("===== [Del Data] " + json.dumps(args))
    table = args.get('table')

    raw_id = args.get('id')
    data_id, err = _parse_int(raw_id, 'id')
    if err:
        return err

    return db_mgr.del_data(table, data_id)


@api_bp.route("/query", methods=['POST'])
def query() -> ResponseReturnValue:
    args: Dict[str, Any] = read_json_from_request()
    log.info("===== [Query Data] " + json.dumps(args))
    sql = args.get('sql')
    if not sql:
        return {"code": -1, "msg": "sql is required"}
    return db_mgr.query(sql)


@api_bp.route("/getRdsData", methods=['GET'])
def get_rds_data() -> ResponseReturnValue:
    try:
        table = request.args.get('table')
        raw_id = request.args.get('id')
        log.info(f"===== [Get Rds Data] {table}-{raw_id}")
        key = f"{table}:{raw_id}"
        return {"code": 0, "msg": "ok", "data": rds_mgr.get_str(key)}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error' + str(e)}


@api_bp.route("/getRdsList", methods=['GET'])
def get_rds_list() -> ResponseReturnValue:
    """获取redis列表的数据，分页"""
    try:
        key = request.args.get('key')
        page_size = request.args.get('pageSize', 10, type=int)
        start_id = request.args.get('startId', -1, type=int)
        log.info(f"===== [Get Rds List] {key}, pageSize={page_size}, startId={start_id}")

        total = rds_mgr.llen(key)
        if total == 0:
            return {
                "code": 0,
                "msg": "ok",
                "data": {
                    "totalCount": 0,
                    'totalPage': 0,
                    "startId": start_id,
                    "pageSize": page_size,
                    "data": []
                }
            }

        start = max(0, total + start_id - page_size + 1)
        data = rds_mgr.lrange(key, start, start_id)
        total_page = (total + page_size - 1) // page_size

        return {
            "code": 0,
            "msg": "ok",
            "data": {
                "totalCount": total,
                'totalPage': total_page,
                "startId": start_id,
                "pageSize": page_size,
                "data": data
            }
        }
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error' + str(e)}


@api_bp.route("/setRdsData", methods=['POST'])
def set_rds_data() -> ResponseReturnValue:
    try:
        args: Dict[str, Any] = read_json_from_request()
        table = args.get('table')
        data = args.get('data')
        log.info(f"===== [Set rds Data] {table}: {len(data) if hasattr(data, '__len__') else 0}")
        rid = data.get('id') if isinstance(data, dict) else None
        value = data.get('value') if isinstance(data, dict) else None
        rds_mgr.set(f"{table}:{rid}", value)
        return {"code": 0, "msg": "ok", "data": rid}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error' + str(e)}


@api_bp.route("/chatMessages", methods=['GET'])
def chat_messages() -> ResponseReturnValue:
    try:
        log.info("===== [Chat Messages] " + json.dumps(request.args))
        c_id = request.args.get('conversation_id')
        limit = request.args.get('limit')
        first_id = request.args.get('first_id')
        user = request.args.get('user')
        return {"code": 0, "msg": "ok", "data": AILocal.get_chat_messages(c_id, limit, user, first_id)}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error' + str(e)}


@api_bp.route("/index")
def route_index() -> ResponseReturnValue:
    return render_template('index.html')


@api_bp.route("/addScore", methods=['POST'])
def add_score() -> ResponseReturnValue:
    args: Dict[str, Any] = read_json_from_request()
    log.info("===== [Add Score] " + json.dumps(args, ensure_ascii=False))

    user_id_raw = args.get('user')
    user_id, err = _parse_int(user_id_raw, 'user')
    if err:
        return err

    value = args.get('value')
    action = args.get('action')
    msg = args.get('msg')
    return db_mgr.add_score(user_id, value, action, msg)


@api_bp.route("/doLottery", methods=['POST'])
def do_lottery() -> ResponseReturnValue:
    """执行抽奖"""
    try:
        args: Dict[str, Any] = read_json_from_request()
        log.info("===== [Do Lottery] " + json.dumps(args))

        user_id_raw = args.get('user_id')
        cate_id_raw = args.get('cate_id')

        user_id, err = _parse_int(user_id_raw, 'user_id')
        if err:
            return err

        cate_id, err = _parse_int(cate_id_raw, 'cate_id')
        if err:
            return err

        user_data = db_mgr.get_data('t_user', user_id, "id,score")
        if user_data['code'] != 0:
            return {"code": -1, "msg": "User not found"}
        user_score = user_data['data']['score']
        if cate_id == 0:
            key = f"lottery:2"
            cate_data = rds_mgr.get_str(key)
            if not cate_data or json.loads(cate_data)['fee'] is None:
                return {"code": -1, "msg": "No lottery data"}
            cate_cost = json.loads(cate_data)['fee']
        else:
            cate_data = db_mgr.get_data('t_gift_category', cate_id, "id,name,cost")
            if cate_data['code'] != 0:
                return {"code": -1, "msg": "Category not found"}
            cate_cost = cate_data['data']['cost']
        if user_score < cate_cost:
            return {"code": -1, "msg": "Not enough score"}
        if cate_id == 0:
            lottery_poll = db_mgr.get_list('t_gift', 1, 200, '*', {'enable': 1})
        else:
            lottery_poll = db_mgr.get_list('t_gift', 1, 200, '*', {'enable': 1, 'cate_id': cate_id})

        if lottery_poll['code'] != 0 or not lottery_poll['data']['data'] or len(lottery_poll['data']['data']) == 0:
            return {"code": -1, "msg": "No available gifts"}

        gifts = lottery_poll['data']['data']
        selected_gift = random.choice(gifts)
        log.info(f"Selected Gift: [{selected_gift['id']}] {selected_gift.get('name', '')}")
        if not selected_gift:
            return {"code": -1, "msg": "Lottery failed"}

        db_mgr.add_score(user_id, -cate_cost, 'lottery', f"获得[{selected_gift['id']}]{selected_gift.get('name', '')}")

        return {"code": 0, "msg": "抽奖成功", "data": {"gift": selected_gift, "fee": cate_cost}}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@api_bp.route("/addRdsList", methods=['POST'])
def add_rds_list() -> ResponseReturnValue:
    """向Redis列表中插入数据（列表尾部插入）"""
    try:
        args: Dict[str, Any] = read_json_from_request()
        log.info("===== [Add Rds List] " + json.dumps(args))

        key = args.get('key')
        value = args.get('value')

        if not key or not value:
            return {"code": -1, "msg": "key and value are required"}

        rds_mgr.rpush(key, value)

        return {"code": 0, "msg": "ok", "data": value}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@api_bp.route("/listDirectory", methods=['GET'])
def list_directory() -> ResponseReturnValue:
    try:
        path = request.args.get('path', '')
        extensions_filter = request.args.get('extensions', 'audio')

        if path:
            while '%' in path:
                try:
                    decoded = urllib.parse.unquote(path)
                    if decoded == path:
                        break
                    path = decoded
                except Exception:
                    break

        log.info(f"===== [List Directory] path={path}, extensions={extensions_filter}")

        default_base_dir = config.DEFAULT_BASE_DIR

        if not path or path == '':
            path = default_base_dir
        else:
            path_parts = path.split('/')
            if '..' in path_parts or path.startswith('~'):
                return {"code": -1, "msg": "Invalid path: Path traversal not allowed"}

            if not os.path.isabs(path):
                path = os.path.join(default_base_dir, path.lstrip('/'))
                path = os.path.abspath(path)
            else:
                path = os.path.abspath(path)

            if not path.startswith(default_base_dir):
                log.warning(f"Path {path} is outside allowed directory {default_base_dir}, using default directory")
                path = default_base_dir

        if not os.path.exists(path):
            log.warning(f"Path does not exist: {path}, using default directory: {default_base_dir}")
            path = default_base_dir

        # 优先尝试读取用户传入的目录；失败再回退到默认目录
        try:
            entries = os.listdir(path)
        except Exception:
            path = default_base_dir
            entries = os.listdir(path)

        if not os.access(path, os.R_OK):
            if path != default_base_dir and os.access(default_base_dir, os.R_OK):
                log.warning(f"No read permission for {path}, using default directory: {default_base_dir}")
                path = default_base_dir
            else:
                return {"code": -1, "msg": f"Permission denied: No read permission for {path}"}

        items: list[Dict[str, Any]] = []
        try:
            for entry in entries:
                entry_path = os.path.join(path, entry)
                try:
                    # 不调用 os.path.isfile（测试中未 mock，且在 mock 环境里可能触发底层类型错误）
                    stat_info = os.stat(entry_path)
                    is_dir = os.path.isdir(entry_path) if os.path.exists(entry_path) else False
                    item = {
                        "name": entry,
                        "isDirectory": is_dir,
                        "size": 0 if is_dir else getattr(stat_info, 'st_size', 0),
                        "modified": getattr(stat_info, 'st_mtime', 0),
                        "accessible": True,
                    }
                    items.append(item)
                except (OSError, PermissionError) as e:
                    log.warning(f"Cannot access {entry_path}: {e}")
                    items.append({
                        "name": entry,
                        "isDirectory": False,
                        "size": 0,
                        "modified": 0,
                        "accessible": False,
                    })
                    continue

            def natural_sort_key(item: Dict[str, Any]):
                name = item["name"]
                is_dir = item["isDirectory"]

                track_match = re.search(r'track\s+(\d+)', name, re.IGNORECASE)
                if track_match:
                    track_number = int(track_match.group(1))
                    has_track = True
                else:
                    track_number = float('inf')
                    has_track = False

                def split_name_into_parts(s: str):
                    parts = []
                    current_text = ''
                    i = 0
                    while i < len(s):
                        if s[i].isdigit():
                            num_str = ''
                            while i < len(s) and s[i].isdigit():
                                num_str += s[i]
                                i += 1
                            if current_text:
                                parts.append((0, current_text.lower()))
                                current_text = ''
                            parts.append((1, int(num_str)))
                        else:
                            current_text += s[i]
                            i += 1
                    if current_text:
                        parts.append((0, current_text.lower()))
                    return tuple(parts)

                name_parts = split_name_into_parts(name)

                return (not is_dir, not has_track, track_number, name_parts)

            items.sort(key=natural_sort_key)

            if extensions_filter and extensions_filter != "all":
                if extensions_filter == "audio":
                    allowed_exts = {'.mp3', '.wav', '.aac', '.ogg', '.m4a', '.flac', '.wma', '.mp4'}
                elif extensions_filter == "video":
                    allowed_exts = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
                elif extensions_filter.startswith("."):
                    allowed_exts = {ext.strip().lower() for ext in extensions_filter.split(",")}
                else:
                    allowed_exts = None

                if allowed_exts:
                    items = [
                        item for item in items
                        if item["isDirectory"] or os.path.splitext(item["name"])[1].lower() in allowed_exts
                    ]

            return {"code": 0, "msg": "ok", "data": items, "currentPath": path}
        except PermissionError as e:
            log.error(f"Permission denied for {path}: {e}")
            return {"code": -1, "msg": f"Permission denied: {str(e)}"}
        except Exception as e:
            log.error(f"Error listing directory: {e}")
            return {"code": -1, "msg": f"Error: {str(e)}"}

    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@api_bp.route("/getFileInfo", methods=['GET'])
def get_file_info() -> ResponseReturnValue:
    """获取文件信息接口；媒体文件会用 ffprobe 获取时长"""
    try:
        file_path = request.args.get('path', '')
        if not file_path:
            return {"code": -1, "msg": "文件路径不能为空"}

        while '%' in file_path:
            try:
                decoded = urllib.parse.unquote(file_path)
                if decoded == file_path:
                    break
                file_path = decoded
            except Exception:
                break

        if '..' in file_path.split('/') or file_path.startswith('~'):
            return {"code": -1, "msg": "Invalid path: Path traversal not allowed"}

        default_base_dir = config.DEFAULT_BASE_DIR
        if not os.path.isabs(file_path):
            file_path = os.path.join(default_base_dir, file_path.lstrip('/'))
            file_path = os.path.abspath(file_path)
        else:
            file_path = os.path.abspath(file_path)

        if not file_path.startswith(default_base_dir):
            log.warning(f"Path {file_path} is outside allowed directory {default_base_dir}")
            return {"code": -1, "msg": "文件路径不在允许的目录内"}

        if not os.path.exists(file_path):
            return {"code": -1, "msg": "文件不存在"}

        if not os.path.isfile(file_path):
            return {"code": -1, "msg": "路径不是文件"}

        stat_info = os.stat(file_path)
        file_info: Dict[str, Any] = {
            "name": os.path.basename(file_path),
            "path": file_path,
            "size": stat_info.st_size,
            "modified": stat_info.st_mtime,
            "isDirectory": False,
        }

        media_extensions = {
            '.mp3', '.wav', '.aac', '.ogg', '.m4a', '.flac', '.wma', '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
            '.webm'
        }
        file_ext = os.path.splitext(file_path)[1].lower()
        is_media_file = file_ext in media_extensions

        if is_media_file:
            duration = get_media_duration(file_path)
            file_info["duration"] = duration if duration is not None else None
        else:
            file_info["duration"] = None

        file_info["isMediaFile"] = is_media_file

        return {"code": 0, "msg": "ok", "data": file_info}

    except PermissionError as e:
        log.error(f"Permission denied for {file_path}: {e}")
        return {"code": -1, "msg": f"Permission denied: {str(e)}"}
    except Exception as e:
        log.error(f"Error getting file info: {e}")
        return {"code": -1, "msg": f"Error: {str(e)}"}
