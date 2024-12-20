from flask import Flask, json, make_response, request, render_template, jsonify
from flask_cors import CORS
import logging
import db_mgr

log = logging.getLogger(__name__)
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type'
    return resp


@app.route("/")
def main():
    return "<p>Hello, World!</p>"


# =========== PIC ===========
@app.route("/getPic", methods=['GET'])
def get_pic():
    id = request.args.get('id')
    log.info("===== [Get Pic] " + id)
    return db_mgr.get_pic(id)


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
    log.info("===== [Set Pic] " + json.dumps(args))
    id = args.get('id')
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


# . .venv/bin/activate
# sudo vim /etc/systemd/system/myTodo.service
# sudo vim /etc/systemd/system/natapp.service
# sudo vim /etc/caddy/Caddyfile
# caddy reload --config=/etc/caddy/Caddyfile
# sudo systemctl restart code-server@orangepi.service
# sudo systemctl daemon-reload
# sudo systemctl restart myTodo.service
if __name__ == '__main__':
    app.run(debug=True, port=8888)  #开始运行flask应用程序，以调试模式运行
