from flask import Flask, json, request, jsonify
from flask_cors import CORS
import logging
import db_mgr

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app)
db_mgr.init_db()


@app.route("/")
def main():
    return "<p>Hello, World!</p>"


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
    user_name = args.get('user_name')
    data = json.dumps(args.get('data'))
    return db_mgr.set_save(id, user_name, data)


# . .venv/bin/activate
# sudo vim /etc/systemd/system/MyTodo.service
# sudo systemctl restart code-server@orangepi.service
# sudo vim  /etc/caddy/Caddyfile
# caddy reload --config=/etc/caddy/Caddyfile
# sudo systemctl restart myTodo.service
if __name__ == '__main__':
    app.run(debug=True, port=8888)  #开始运行flask应用程序，以调试模式运行
