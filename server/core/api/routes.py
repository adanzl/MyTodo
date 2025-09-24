from core.db.db_mgr import DB_Mgr as db_mgr

from core.log_config import root_logger
from flask import Blueprint, json, jsonify, render_template, request
import core.db.rds_mgr as rds_mgr
from core.ai.ai_local import AILocal
import random

log = root_logger()
api_bp = Blueprint('api', __name__)


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
    conditions_str = request.args.get('conditions')
    conditions = json.loads(conditions_str) if conditions_str else None
    table = request.args.get('table')
    log.info("===== [Get All Data] " + json.dumps(request.args))
    if fields != '*':
        fields = fields.split(',')
    return db_mgr.get_list(table, page_num, page_size, fields, conditions)


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
        return {"code": 0, "msg": "ok", "data": rds_mgr.get_str(key)}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error' + str(e)}


@api_bp.route("/getRdsList", methods=['GET'])
def get_rds_list():
    '''
    获取redis列表的数据，分页
    '''
    try:
        key = request.args.get('key')
        page_size = request.args.get('pageSize', 10, type=int)
        start_id = request.args.get('startId', -1, type=int)
        log.info(f"===== [Get Rds List] {key}, pageSize={page_size}, startId={start_id}")

        # 获取列表总长度
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

        # 获取指定范围的数据
        start = max(0, total + start_id - page_size + 1)  # 确保起始索引不小于0
        data = rds_mgr.lrange(key, start, start_id)
        # 计算总页数
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
def set_rds_data():
    try:
        args = request.get_json()
        log.info("===== [Set rds Data] " + json.dumps(args))
        table = args.get('table')
        data = args.get('data')
        id = data.get('id')
        value = data.get('value')
        rds_mgr.set(f"{table}:{id}", value)
        return {"code": 0, "msg": "ok", "data": id}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error' + str(e)}


@api_bp.route("/chatMessages", methods=['GET'])
def chat_messages():
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
def route_index():
    return render_template('index.html')


@api_bp.route("/addScore", methods=['POST'])
def add_score():
    args = request.get_json()
    log.info("===== [Add Score] " + json.dumps(args))
    user = args.get('user')
    value = args.get('value')
    action = args.get('action')
    msg = args.get('msg')
    return db_mgr.add_score(user, value, action, msg)


@api_bp.route("/doLottery", methods=['POST'])
def do_lottery():
    """
    执行抽奖
    """
    try:
        args = request.get_json()
        log.info("===== [Do Lottery] " + json.dumps(args))

        user_id = args.get('user_id')
        cate_id = args.get('cate_id')

        if user_id is None or cate_id is None:
            return {"code": -1, "msg": "user_id and cate_id are required"}
        user_data = db_mgr.get_data('t_user', user_id, "id,score")
        if user_data['code'] != 0:
            return {"code": -1, "msg": "User not found"}
        user_score = user_data['data']['score']
        if cate_id == 0:
            key = f"lottery:2"
            cate_data = rds_mgr.get_str(key)
            if not cate_data or cate_data['fee'] is None:
                return {"code": -1, "msg": "No lottery data"}
            cate_cost = cate_data['fee']
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

        # 检查奖品池是否为空
        if lottery_poll['code'] != 0 or not lottery_poll['data'] or len(lottery_poll['data']) == 0:
            return {"code": -1, "msg": "No available gifts"}

        # 随机抽奖逻辑
        gifts = lottery_poll['data']
        selected_gift = random.choice(gifts)

        if not selected_gift:
            return {"code": -1, "msg": "Lottery failed"}
        # 扣除积分
        db_mgr.add_score(user_id, -cate_cost, 'lottery', f"获得[{selected_gift['id']}]{selected_gift.get('name', '')}")

        return {"code": 0, "msg": "抽奖成功", "data": {"gift": selected_gift, "cost": cate_cost}}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": 'error: ' + str(e)}


@api_bp.route("/addRdsList", methods=['POST'])
def add_rds_list():
    """
    向Redis列表中插入数据
    支持在列表头部或尾部插入数据
    """
    try:
        args = request.get_json()
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
