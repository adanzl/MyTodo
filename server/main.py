import logging
from logging.handlers import TimedRotatingFileHandler

import core.ai.ai_mgr as ai_mgr
import core.db.db_mgr as db_mgr
from core.api.routes import api_bp
from core.chat.chat_mgr import ChatMgr
from flask import Flask, make_response
from flask_cors import CORS
from flask_socketio import SocketIO

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = TimedRotatingFileHandler('logs/app.log', when="midnight", backupCount=3, encoding="utf-8")
std_handler = logging.StreamHandler()
std_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[file_handler,std_handler])

log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
# 创建 SocketIO 实例并与 Flask 应用关联
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

chat_mgr = ChatMgr(socketio)
db_mgr.init()
ai_mgr.init()

app.register_blueprint(api_bp, url_prefix='/')


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

# . .venv/bin/activate
if __name__ == '__main__':
    #开始运行flask应用程序，以调试模式运行
    # app.run(debug=True, port=8888)
    socketio.run(app, debug=True, port=8000)
