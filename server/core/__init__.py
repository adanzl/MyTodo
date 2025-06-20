from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

import core.ai.ai_mgr as ai_mgr
from core.api.routes import api_bp
from core.chat.chat_mgr import ChatMgr
from core.db.db_mgr import DB_Mgr
import os


def create_app():
    instance_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(__name__, instance_path=instance_path, instance_relative_config=True)

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

    ChatMgr(socketio)
    DB_Mgr.init(app)
    ai_mgr.init()

    return app


from core.models import *
