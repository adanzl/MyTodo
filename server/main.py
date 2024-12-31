from flask import Flask, json, make_response, request, render_template, jsonify
from flask_cors import CORS
import logging
import db_mgr

from logging.handlers import TimedRotatingFileHandler

handler = TimedRotatingFileHandler('logs/app.log', when="midnight", backupCount=3, encoding="utf-8")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.addHandler(handler)
app = Flask(__name__)
CORS(app, supports_credentials=True)
db_mgr.init_db()


@app.after_request
def af_request(resp):
    """
    #请求钩子，在所有的请求发生后执行，加入headers。
    :param resp:
    :return:
    """
    resp = make_response(resp)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp


@app.route("/")
def main():
    return "<p>Hello, World!</p>"


@app.route("/natapp")
def natapp():
    with open("/usr/env/natapp/log/natapp.log", "r") as f:
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


@app.route("/log")
def server_log():
    with open("logs/app.log", "r") as f:
        log_content = f.read()
        return f"""
            <html>
            <head>
                <title>Server Log</title>
            </head>
            <body>
                <pre>{log_content}</pre>
            </body>
            </html>
        """


# =========== PIC ===========
@app.route("/getPic", methods=['GET'])
def get_pic():
    id = request.args.get('id')
    log.info("===== [Get Pic] " + id)
    return db_mgr.get_pic(id)


@app.route("/getAllPic", methods=['GET'])
def get_all_pic():
    page_size = request.args.get('pageSize', 20, type=int)
    page_num = request.args.get('pageNum', 1, type=int)
    log.info("===== [Get All Pic] ", page_num, page_size)
    return db_mgr.get_all_pic(page_num, page_size)


@app.route("/viewPic", methods=['GET'])
def view_pic():
    id = request.args.get('id')
    log.info("===== [View Pic] " + id)
    p_data = db_mgr.get_pic(id)
    if p_data['code'] == 0:
        return render_template('image.html', image_data=p_data['data'])
    else:
        return jsonify({'error': 'Image not found'}), 404


@app.route("/setPic", methods=['POST'])
def set_pic():
    args = request.get_json()
    id = args.get('id')
    log.info("===== [Set Pic] id: " + id)
    data = args.get('data')
    return db_mgr.set_pic(id, data)


@app.route("/delPic", methods=['POST'])
def del_pic():
    args = request.get_json()
    log.info("===== [Del Pic] " + json.dumps(args))
    id = args.get('id')
    return db_mgr.del_pic(id)


# =========== SAVE ===========
@app.route("/getSave", methods=['GET'])
def get_save():
    id = request.args.get('id')
    log.info("===== [Get Save] " + id)
    return db_mgr.get_save(id)


@app.route("/setSave", methods=['POST'])
def set_save():
    args = request.get_json()
    log.info("===== [Set Save] " + json.dumps(args))
    id = args.get('id')
    user = args.get('user')
    data = json.dumps(args.get('data'))
    return db_mgr.set_save(id, user, data)


# =========== Common ===========
@app.route("/getAll", methods=['GET'])
def get_all():
    page_size = request.args.get('pageSize', 20, type=int)
    page_num = request.args.get('pageNum', 1, type=int)
    table = request.args.get('table')
    log.info("===== [Get All Data] ", table, page_num, page_size)
    return db_mgr.get_list(table, page_num, page_size)


@app.route("/getData", methods=['GET'])
def get_data():
    table = request.args.get('table')
    id = request.args.get('id')
    idx = request.args.get('idx', 1)
    log.info("===== [Get Data] ", table, id)
    return db_mgr.get_data(table, id, idx)


@app.route("/setData", methods=['POST'])
def set_data():
    args = request.get_json()
    log.info("===== [Set Data] " + json.dumps(args))
    table = args.get('table')
    id = args.get('id')
    data = json.dumps(args.get('data'))
    return db_mgr.set_data(table, id, data)


@app.route("/delData", methods=['POST'])
def del_data():
    args = request.get_json()
    log.info("===== [Del Data] " + json.dumps(args))
    table = args.get('table')
    id = args.get('id')
    return db_mgr.del_data(table, id)


# . .venv/bin/activate
if __name__ == '__main__':
    app.run(debug=True, port=8888)  #开始运行flask应用程序，以调试模式运行
