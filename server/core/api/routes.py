from core.db.db_mgr import db_mgr

from core.log_config import root_logger
from flask import Blueprint, json, jsonify, render_template, request
import core.db.rds_mgr as rds_mgr
from core.ai.ai_local import AILocal
from core.utils import get_media_duration, read_json_from_request
import random
import os
import re
import subprocess
import urllib.parse

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
    args = read_json_from_request()
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
    args = read_json_from_request()
    log.info("===== [Set Data] " + len(args))
    table = args.get('table')
    data = args.get('data')
    return db_mgr.set_data(table, data)


@api_bp.route("/delData", methods=['POST'])
def del_data():
    args = read_json_from_request()
    log.info("===== [Del Data] " + json.dumps(args))
    table = args.get('table')
    id = args.get('id')
    return db_mgr.del_data(table, id)


@api_bp.route("/query", methods=['POST'])
def query():
    args = read_json_from_request()
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
        args = read_json_from_request()
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
    args = read_json_from_request()
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
        args = read_json_from_request()
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
        # log.info(f"Lottery Poll: {lottery_poll}")
        # 检查奖品池是否为空
        if lottery_poll['code'] != 0 or not lottery_poll['data']['data'] or len(lottery_poll['data']['data']) == 0:
            return {"code": -1, "msg": "No available gifts"}

        # 随机抽奖逻辑
        gifts = lottery_poll['data']['data']
        selected_gift = random.choice(gifts)
        log.info(f"Selected Gift: [{selected_gift['id']}] {selected_gift.get('name', '')}")
        if not selected_gift:
            return {"code": -1, "msg": "Lottery failed"}
        # 扣除积分
        db_mgr.add_score(user_id, -cate_cost, 'lottery', f"获得[{selected_gift['id']}]{selected_gift.get('name', '')}")

        return {"code": 0, "msg": "抽奖成功", "data": {"gift": selected_gift, "fee": cate_cost}}
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
        args = read_json_from_request()
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
def list_directory():
    try:
        path = request.args.get('path', '')
        extensions_filter = request.args.get('extensions', 'audio')  # 默认筛选音频

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

        default_base_dir = '/mnt'

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

            if not path.startswith('/mnt'):
                log.warning(f"Path {path} is outside allowed directory /mnt, using default directory")
                path = default_base_dir

        if not os.path.exists(path):
            log.warning(f"Path does not exist: {path}, using default directory: {default_base_dir}")
            path = default_base_dir

        if not os.path.isdir(path):
            log.warning(f"Path is not a directory: {path}, using default directory: {default_base_dir}")
            path = default_base_dir

        if not os.access(path, os.R_OK):
            if path != default_base_dir and os.access(default_base_dir, os.R_OK):
                log.warning(f"No read permission for {path}, using default directory: {default_base_dir}")
                path = default_base_dir
            else:
                return {"code": -1, "msg": f"Permission denied: No read permission for {path}"}

        items = []
        try:
            entries = os.listdir(path)
            for entry in entries:
                entry_path = os.path.join(path, entry)
                try:
                    if not os.access(entry_path, os.R_OK):
                        items.append({
                            "name": entry,
                            "isDirectory": os.path.isdir(entry_path) if os.path.exists(entry_path) else False,
                            "size": 0,
                            "modified": 0,
                            "accessible": False,
                        })
                        continue

                    stat_info = os.stat(entry_path)
                    item = {
                        "name": entry,
                        "isDirectory": os.path.isdir(entry_path),
                        "size": stat_info.st_size if os.path.isfile(entry_path) else 0,
                        "modified": stat_info.st_mtime,
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

            # 自然排序函数：按文件名中的数字排序
            def natural_sort_key(item):
                name = item["name"]
                is_dir = item["isDirectory"]

                # 优先查找 "Track" 后面的数字（不区分大小写）
                track_match = re.search(r'track\s+(\d+)', name, re.IGNORECASE)
                if track_match:
                    # 如果找到 Track 数字，使用它作为主要排序键
                    track_number = int(track_match.group(1))
                    has_track = True
                else:
                    track_number = float('inf')
                    has_track = False

                # 将文件名转换为自然排序的元组：将数字和文本分开
                # 例如 "p1.mp3" -> (0, 'p', 1, '.mp3'), "1abc.mp3" -> (1, 'abc', '.mp3')
                # 使用 (类型标识, 值) 的格式确保类型安全比较
                # 类型标识：0=文本, 1=数字，确保文本总是排在数字前面
                def split_name_into_parts(s):
                    parts = []
                    current_text = ''
                    i = 0
                    while i < len(s):
                        if s[i].isdigit():
                            # 开始读取数字
                            num_str = ''
                            while i < len(s) and s[i].isdigit():
                                num_str += s[i]
                                i += 1
                            if current_text:
                                parts.append((0, current_text.lower()))  # 0 表示文本
                                current_text = ''
                            parts.append((1, int(num_str)))  # 1 表示数字
                        else:
                            current_text += s[i]
                            i += 1
                    if current_text:
                        parts.append((0, current_text.lower()))  # 0 表示文本
                    return tuple(parts)

                name_parts = split_name_into_parts(name)

                # 返回排序键：(是否目录, 是否有Track数字, Track数字, 文件名自然排序元组)
                # 目录排在前面，然后有Track数字的文件按Track数字排序，没有Track数字的文件按自然排序
                return (
                    not is_dir,  # False (目录) 排在 True (文件) 前面
                    not has_track,  # False (有Track数字) 排在 True (无Track数字) 前面
                    track_number,  # Track 数字（主要排序键）
                    name_parts  # 文件名自然排序元组，每个元素是 (类型标识, 值) 格式
                )

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
def get_file_info():
    """
    获取文件信息接口
    如果是媒体文件，使用 ffprobe 获取时长
    """
    try:
        file_path = request.args.get('path', '')
        if not file_path:
            return {"code": -1, "msg": "文件路径不能为空"}

        # URL 解码
        while '%' in file_path:
            try:
                decoded = urllib.parse.unquote(file_path)
                if decoded == file_path:
                    break
                file_path = decoded
            except Exception:
                break

        # 安全检查：防止路径遍历
        if '..' in file_path.split('/') or file_path.startswith('~'):
            return {"code": -1, "msg": "Invalid path: Path traversal not allowed"}

        # 处理相对路径
        default_base_dir = '/mnt'
        if not os.path.isabs(file_path):
            file_path = os.path.join(default_base_dir, file_path.lstrip('/'))
            file_path = os.path.abspath(file_path)
        else:
            file_path = os.path.abspath(file_path)

        # 检查路径是否在允许的目录内
        if not file_path.startswith('/mnt'):
            log.warning(f"Path {file_path} is outside allowed directory /mnt")
            return {"code": -1, "msg": "文件路径不在允许的目录内"}

        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {"code": -1, "msg": "文件不存在"}

        if not os.path.isfile(file_path):
            return {"code": -1, "msg": "路径不是文件"}

        # 获取文件基本信息
        stat_info = os.stat(file_path)
        file_info = {
            "name": os.path.basename(file_path),
            "path": file_path,
            "size": stat_info.st_size,
            "modified": stat_info.st_mtime,
            "isDirectory": False,
        }

        # 判断是否为媒体文件
        media_extensions = {
            '.mp3',
            '.wav',
            '.aac',
            '.ogg',
            '.m4a',
            '.flac',
            '.wma',  # 音频
            '.mp4',
            '.avi',
            '.mkv',
            '.mov',
            '.wmv',
            '.flv',
            '.webm'  # 视频
        }
        file_ext = os.path.splitext(file_path)[1].lower()
        is_media_file = file_ext in media_extensions

        if is_media_file:
            # 使用 ffprobe 获取媒体文件时长
            duration = get_media_duration(file_path)
            if duration is not None:
                file_info["duration"] = duration
            else:
                file_info["duration"] = None
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
