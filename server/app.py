from flask import Flask, make_response
from flask_cors import CORS
from flask_socketio import SocketIO
from core.api.routes import api_bp

app = Flask(__name__, static_url_path='')

CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
# 创建 SocketIO 实例并与 Flask 应用关联
socketio = SocketIO(
    app,
    async_mode='gevent',
    cors_allowed_origins="*",
    ping_timeout=60,  # 增加超时时间
    ping_interval=25,  # 增加心跳间隔
)

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
