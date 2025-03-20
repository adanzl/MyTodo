import core.db.db_mgr as db_mgr
import redis
from core.log_config import root_logger
from flask import Blueprint, json, jsonify, render_template, request

log = root_logger()
api_bp = Blueprint('api', __name__)
rds = redis.Redis(
    host='192.168.50.171',  # Redis服务器地址，默认为localhost
    port=6379,  # Redis服务器端口，默认为6379
    db=0,  # 使用的数据库编号，默认为0
    password=None,  # 如果Redis设置了密码，则在这里填写
    decode_responses=True  # 是否将返回的数据自动解码为字符串
)


@api_bp.route("/natapp")
def natapp():
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
def server_log():
    with open("logs/app.log", "r") as f:
        # 读取文件所有行
        lines = f.readlines()
        # 反转行的顺序
        lines.reverse()
        log_content = ''.join(lines)
    return render_template('server_log.html', log_content=log_content)



@api_bp.route("/write_log", methods=['POST'])
def write_log():
    try:
        args = request.get_data().decode('utf-8')
        log.info("===== [Write Log] " + args)
    except Exception as e:
        log.error(e)
    return {}


# =========== PIC ===========
@api_bp.route("/viewPic", methods=['GET'])
def view_pic():
    id = request.args.get('id')
    log.info("===== [View Pic] " + id)
    p_data = db_mgr.get_data_idx(db_mgr.TABLE_PIC, id)
    if p_data['code'] == 0:
        return render_template('image.html', image_data=p_data['data'])
    else:
        return jsonify({'error': 'Image not found'}), 404


# =========== SAVE ===========
@api_bp.route("/getSave", methods=['GET'])
def get_save():
    id = request.args.get('id')
    log.info("===== [Get Save] ", id)
    return db_mgr.get_save(id)


@api_bp.route("/setSave", methods=['POST'])
def set_save():
    args = request.get_json()
    log.info("===== [Set Save] " + json.dumps(args))
    id = args.get('id')
    user = args.get('user')
    data = json.dumps(args.get('data'))
    return db_mgr.set_save(id, user, data)


# =========== Common ===========
@api_bp.route("/getAll", methods=['GET'])
def get_all():
    page_size = request.args.get('pageSize', 20, type=int)
    page_num = request.args.get('pageNum', 1, type=int)
    fields = request.args.get('fields', '*')
    table = request.args.get('table')
    log.info("===== [Get All Data] " + json.dumps(request.args))
    if fields != '*':
        fields = fields.split(',')
    return db_mgr.get_list(table, page_num, page_size, fields)


@api_bp.route("/getData", methods=['GET'])
def get_data():
    table = request.args.get('table')
    id = request.args.get('id')
    idx = request.args.get('idx', type=int)
    fields = request.args.get('fields')
    log.info("===== [Get Data] " + json.dumps(request.args))
    if (fields is None):
        return db_mgr.get_data_idx(table, id, idx)
    else:
        return db_mgr.get_data(table, id, fields)


@api_bp.route("/setData", methods=['POST'])
def set_data():
    args = request.get_json()
    log.info("===== [Set Data] " + json.dumps(args))
    table = args.get('table')
    data = args.get('data')
    return db_mgr.set_data(table, data)


@api_bp.route("/delData", methods=['POST'])
def del_data():
    args = request.get_json()
    log.info("===== [Del Data] " + json.dumps(args))
    table = args.get('table')
    id = args.get('id')
    return db_mgr.del_data(table, id)


@api_bp.route("/query", methods=['POST'])
def query():
    args = request.get_json()
    log.info("===== [Query Data] " + json.dumps(args))
    sql = args.get('sql')
    return db_mgr.query(sql)


@api_bp.route("/getRdsData", methods=['GET'])
def get_rds_data():
    try:
        table = request.args.get('table')
        id = request.args.get('id')
        log.info(f"===== [Get Rds Data] {table}-{id}")
        key = f"{table}:{id}"
        return {"code": 0, "msg": "ok", "data": rds.get(key)}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error' + str(e)}


@api_bp.route("/setRdsData", methods=['POST'])
def set_rds_data():
    try:
        args = request.get_json()
        log.info("===== [Set rds Data] " + json.dumps(args))
        table = args.get('table')
        data = args.get('data')
        id = data.get('id')
        value = data.get('value')
        rds.set(f"{table}:{id}", value)
        return {"code": 0, "msg": "ok", "data": id}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error' + str(e)}
