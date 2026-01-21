from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 全局限流实例，供各路由模块装饰器使用
limiter = Limiter(key_func=get_remote_address)
from flask_sqlalchemy import SQLAlchemy
from flask_smorest import Api

# 必须在导入任何使用 miservice 的模块之前 patch fake_useragent
# 避免 fake_useragent 的 ThreadPoolExecutor 在 gevent 环境中导致 LoopExit
from core.tools.useragent_fix import patch_fake_useragent

patch_fake_useragent()

import core.ai.ai_mgr as ai_mgr
from core.chat.chat_mgr import chat_mgr
from core.db.db_mgr import db_mgr
from core.services.scheduler_mgr import scheduler_mgr
from core.config import config
import os


def create_app():
    instance_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(__name__, instance_path=instance_path, instance_relative_config=True)

    # OpenAPI / Swagger UI
    app.config.setdefault("API_TITLE", "MyTodo Server API")
    app.config.setdefault("API_VERSION", "v1")
    app.config.setdefault("OPENAPI_VERSION", "3.0.3")
    app.config.setdefault("OPENAPI_URL_PREFIX", "/")
    app.config.setdefault("OPENAPI_SWAGGER_UI_PATH", "/docs")
    app.config.setdefault("OPENAPI_SWAGGER_UI_URL", "https://cdn.jsdelivr.net/npm/swagger-ui-dist/")
    Api(app)

    # 配置限流（全局默认）
    limiter = Limiter(key_func=get_remote_address)
    limiter.init_app(
        app,
        default_limits=[config.RATE_LIMIT_DEFAULT],
        storage_uri=config.RATE_LIMIT_STORAGE_URI,
    )

    # 配置允许上传大文件
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

    # 统一使用配置中的 CORS 来源
    cors_origins = config.get_cors_origins()
    # Flask-CORS 配置：如果 origins 是 ['*']，需要特殊处理
    if cors_origins == ['*']:
        CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
        socketio_cors_origins = "*"
    else:
        CORS(app, supports_credentials=True, resources={r"/*": {"origins": cors_origins}})
        socketio_cors_origins = cors_origins

    # 创建 SocketIO 实例并与 Flask 应用关联
    socketio = SocketIO(
        app,
        async_mode='gevent',
        cors_allowed_origins=socketio_cors_origins,
        ping_timeout=60,  # 增加超时时间
        ping_interval=25,  # 增加心跳间隔
    )

    from core.api.routes import api_bp
    from core.api.agent_routes import agent_bp
    from core.api.bluetooth_routes import bluetooth_bp
    from core.api.dlna_routes import dlna_bp
    from core.api.media_routes import media_bp
    from core.api.playlist_routes import playlist_bp
    from core.api.mi_routes import mi_bp
    from core.api.pdf_routes import pdf_bp

    app.register_blueprint(api_bp, url_prefix='/')
    app.register_blueprint(agent_bp, url_prefix='/')
    app.register_blueprint(bluetooth_bp, url_prefix='/')
    app.register_blueprint(media_bp, url_prefix='/')
    app.register_blueprint(playlist_bp, url_prefix='/')
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
