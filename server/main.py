from flask import Flask, json, make_response, request, render_template, jsonify
from flask_cors import CORS
import logging
import db_mgr
import ai_mgr

from logging.handlers import TimedRotatingFileHandler

handler = TimedRotatingFileHandler('logs/app.log', when="midnight", backupCount=3, encoding="utf-8")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.addHandler(handler)
app = Flask(__name__)
CORS(app, supports_credentials=True)
db_mgr.init()
ai_mgr.init()


@app.after_request
def af_request(resp):
    """
    #请求钩子，在所有的请求发生后执行，加入headers。
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
@app.route("/viewPic", methods=['GET'])
def view_pic():
    id = request.args.get('id')
    log.info("===== [View Pic] " + id)
    p_data = db_mgr.get_data(db_mgr.TABLE_PIC, id)
    if p_data['code'] == 0:
        return render_template('image.html', image_data=p_data['data'])
    else:
        return jsonify({'error': 'Image not found'}), 404


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
    idx = request.args.get('idx', 1, type=int)
    log.info("===== [Get Data] ", table, id, idx)
    return db_mgr.get_data(table, id, idx)


@app.route("/setData", methods=['POST'])
def set_data():
    args = request.get_json()
    log.info("===== [Set Data] " + json.dumps(args))
    table = args.get('table')
    data = args.get('data')
    return db_mgr.set_data(table, data)


@app.route("/delData", methods=['POST'])
def del_data():
    args = request.get_json()
    log.info("===== [Del Data] " + json.dumps(args))
    table = args.get('table')
    id = args.get('id')
    return db_mgr.del_data(table, id)

@app.route("/query", methods=['POST'])
def query():
    args = request.get_json()
    log.info("===== [Query Data] " + json.dumps(args))
    sql = args.get('sql')
    return db_mgr.query(sql)

# ai
@app.route("/chat", methods=['POST'])
def chat():
    args = request.get_json()
    log.info("===== [Chat] " + json.dumps(args, ensure_ascii=False))
    # return db_mgr.get_ai_list(page_num, page_size) 
    prompt = args.get('prompt')
    if not prompt:
        return jsonify({"error": "缺少 prompt 参数"}), 400
    result = ai_mgr.call_doubao_api(prompt)
    if result:
        return jsonify(result)
    else:
        return jsonify({"error": "调用 API 失败"}), 500

# . .venv/bin/activate
if __name__ == '__main__':
    app.run(debug=True, port=8888)  #开始运行flask应用程序，以调试模式运行
