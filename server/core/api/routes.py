"""通用 API 路由模块（api_bp）"""

from __future__ import annotations

from typing import Any, Dict, Optional

import core.db.rds_mgr as rds_mgr
from core.ai.ai_local import AILocal
from core.config import app_logger
from core.db.db_mgr import db_mgr
from core.services.file_mgr import file_mgr
from core.utils import read_json_from_request
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
        log.info("=> [Write Log] " + args)
    except Exception as e:
        log.error(e)
    return {}


# =========== SAVE ==========
@api_bp.route("/getSave", methods=['GET'])
def get_save() -> ResponseReturnValue:
    raw_id = request.args.get('id')
    log.info(f"=> [Get Save] id={raw_id}")

    save_id, err = _parse_int(raw_id, 'id')
    if err:
        return err

    return db_mgr.get_save(save_id)


@api_bp.route("/setSave", methods=['POST'])
def set_save() -> ResponseReturnValue:
    args: Dict[str, Any] = read_json_from_request()
    log.info("=> [Set Save] " + json.dumps(args))

    raw_id = args.get('id')
    save_id, err = _parse_int(raw_id, 'id')
    if err:
        return err

    user = args.get('user')
    data = json.dumps(args.get('data'))
    return db_mgr.set_save(save_id, user, data)


# =========== Common ==========
@api_bp.route("/getAllUser", methods=['GET'])
def get_all_user() -> ResponseReturnValue:
    """返回用户列表，与 getAll 传 table=t_user 时参数和返回格式一致。"""
    page_size = request.args.get('pageSize', 20, type=int)
    page_num = request.args.get('pageNum', 1, type=int)
    fields = request.args.get('fields', '*')
    conditions_str = request.args.get('conditions')
    conditions = json.loads(conditions_str) if conditions_str else None
    if fields != '*':
        fields = fields.split(',')
    return db_mgr.get_list('t_user', page_num, page_size, fields, conditions)


@api_bp.route("/getAll", methods=['GET'])
def get_all() -> ResponseReturnValue:
    page_size = request.args.get('pageSize', 20, type=int)
    page_num = request.args.get('pageNum', 1, type=int)
    fields = request.args.get('fields', '*')
    conditions_str = request.args.get('conditions')
    conditions = json.loads(conditions_str) if conditions_str else None
    table = request.args.get('table')
    if table is None:
        return {"code": -1, "msg": "table is required"}
    # log.info("=> [Get All Data] " + json.dumps(request.args))
    if fields != '*':
        fields = fields.split(',')
    return db_mgr.get_list(table, page_num, page_size, fields, conditions)


@api_bp.route("/getData", methods=['GET'])
def get_data() -> ResponseReturnValue:
    table = request.args.get('table')
    raw_id = request.args.get('id')
    idx = request.args.get('idx', default=1, type=int)
    fields = request.args.get('fields')
    # log.info("=> [Get Data] " + json.dumps(request.args))

    data_id, err = _parse_int(raw_id, 'id')
    if err:
        return err
    if table is None or data_id is None:
        return {"code": -1, "msg": "table or id is required"}
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
    if table is None or data is None:
        return {"code": -1, "msg": "table or data is required"}
    log.info(f"=> [Set Data] {table}: {data}")
    return db_mgr.set_data(table, data)


@api_bp.route("/user/update", methods=['POST'])
def update_user() -> ResponseReturnValue:
    """
    更新用户信息（安全接口）
    只允许更新：name, icon, admin, wish_list
    禁止更新：score, wish_progress（这些字段由系统自动管理）
    """
    args: Dict[str, Any] = read_json_from_request()
    log.info(f"=> [Update User] {args}")

    # 必须包含 id
    user_id = args.get('id')
    if user_id is None:
        return {"code": -1, "msg": "user id is required"}

    # 定义允许更新的字段白名单
    allowed_fields = {'id', 'name', 'icon', 'admin', 'wish_list'}

    # 过滤数据，只保留允许的字段
    filtered_data = {}
    for key, value in args.items():
        if key in allowed_fields:
            filtered_data[key] = value
        else:
            log.warning(f"[Update User] 拒绝更新不允许的字段: {key}")

    if not filtered_data or 'id' not in filtered_data:
        return {"code": -1, "msg": "no valid fields to update"}

    return db_mgr.set_data('t_user', filtered_data)


@api_bp.route("/delData", methods=['POST'])
def del_data() -> ResponseReturnValue:
    args: Dict[str, Any] = read_json_from_request()
    log.info("=> [Del Data] " + json.dumps(args))
    table = args.get('table')

    raw_id = args.get('id')
    data_id, err = _parse_int(raw_id, 'id')

    if table is None or data_id is None:
        return {"code": -1, "msg": "table or id is required"}
    if err:
        return err

    return db_mgr.del_data(table, data_id)


@api_bp.route("/query", methods=['POST'])
def query() -> ResponseReturnValue:
    args: Dict[str, Any] = read_json_from_request()
    log.info("=> [Query Data] " + json.dumps(args))
    sql = args.get('sql')
    if not sql:
        return {"code": -1, "msg": "sql is required"}
    return db_mgr.query(sql)


@api_bp.route("/getRdsData", methods=['GET'])
def get_rds_data() -> ResponseReturnValue:
    try:
        table = request.args.get('table')
        raw_id = request.args.get('id')
        # log.info(f"=> [Get Rds Data] {table}-{raw_id}")
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
        page_size = request.args.get('pageSize', 20, type=int)
        start_id = request.args.get('startId', -1, type=int)
        log.info(f"=> [Get Rds List] {key}, pageSize={page_size}, startId={start_id}")
        if key is None:
            return {"code": -1, "msg": "key is required"}

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
        if table is None or data is None:
            return {"code": -1, "msg": "table or data is required"}
        log.info(f"=> [Set rds Data] {table}: {len(data) if hasattr(data, '__len__') else 0}")
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
        log.info("=> [Chat Messages] " + json.dumps(request.args, ensure_ascii=False))
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
    log.info("=> [Add Score] " + json.dumps(args, ensure_ascii=False))

    user_id_raw = args.get('user')
    user_id, err = _parse_int(user_id_raw, 'user')
    if err:
        return err

    value = args.get('value')
    action = args.get('action')
    msg = args.get('msg')
    if value is None or action is None or user_id is None:
        return {"code": -1, "msg": "value or action or user_id is required"}
    return db_mgr.add_score(user_id, value, action, msg)


@api_bp.route("/addRdsList", methods=['POST'])
def add_rds_list() -> ResponseReturnValue:
    """向Redis列表中插入数据（列表尾部插入）"""
    try:
        args: Dict[str, Any] = read_json_from_request()
        log.info("=> [Add Rds List] " + json.dumps(args))

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
    """列出目录内容"""
    path = request.args.get('path', '')
    extensions_filter = request.args.get('extensions', 'audio')
    recursive = request.args.get('recursive', 'false').lower() == 'true'

    result = file_mgr.list_directory(path, extensions_filter, recursive)
    return result


@api_bp.route("/getFileInfo", methods=['GET'])
def get_file_info() -> ResponseReturnValue:
    """获取文件信息接口；媒体文件会用 ffprobe 获取时长"""
    file_path = request.args.get('path', '')
    result = file_mgr.get_file_info(file_path)
    return result
