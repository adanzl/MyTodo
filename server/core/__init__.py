from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

import core.ai.ai_mgr as ai_mgr
from core.api.routes import api_bp
from core.api.agent_routes import agent_bp
from core.api.bluetooth_routes import bluetooth_bp
from core.api.dlna_routes import dlna_bp
from core.api.media_routes import media_bp
from core.api.media_plan_routes import media_plan_bp
from core.api.mi_routes import mi_bp
from core.api.pdf_routes import pdf_bp
from core.chat.chat_mgr import chat_mgr
from core.db.db_mgr import db_mgr
from core.services.scheduler_mgr import scheduler_mgr
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
    app.register_blueprint(agent_bp, url_prefix='/')
    app.register_blueprint(bluetooth_bp, url_prefix='/')
    app.register_blueprint(media_bp, url_prefix='/')
    app.register_blueprint(media_plan_bp, url_prefix='/')
    app.register_blueprint(dlna_bp, url_prefix='/')
    app.register_blueprint(mi_bp, url_prefix='/')
    app.register_blueprint(pdf_bp, url_prefix='/')

    chat_mgr.init(socketio)
    db_mgr.init(app)
    ai_mgr.init()

    # 初始化定时任务调度器
    scheduler_mgr.start()
    return app


from core.models import *
