from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 全局限流实例，供各路由模块装饰器使用
limiter = Limiter(key_func=get_remote_address)
from flask_sqlalchemy import SQLAlchemy
from flask_smorest import Api
from datetime import timedelta

from flask_jwt_extended import (JWTManager, create_access_token, create_refresh_token, set_refresh_cookies,
                                unset_jwt_cookies, verify_jwt_in_request)

# 必须在导入任何使用 miservice 的模块之前 patch fake_useragent
# 避免 fake_useragent 的 ThreadPoolExecutor 在 gevent 环境中导致 LoopExit
from core.tools.useragent_fix import patch_fake_useragent

patch_fake_useragent()

import core.ai.ai_mgr as ai_mgr
from core.chat.chat_mgr import chat_mgr
from core.db.db_mgr import db_mgr
from core.services.scheduler_mgr import scheduler_mgr
from core.config import config, app_logger, access_logger
import json
import os
import time

log = app_logger


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

    # OPTIONS 预检短路：必须在 limiter 之前注册，避免 OPTIONS 走限流等逻辑导致延迟
    @app.before_request
    def _short_circuit_options():
        if request.method == 'OPTIONS':
            request._start_time = time.time()
            return '', 200

    # 配置限流（全局默认）
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[config.RATE_LIMIT_DEFAULT],
        storage_uri=config.RATE_LIMIT_STORAGE_URI,
    )
    limiter.init_app(app)

    # 配置允许上传大文件
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

    # 统一使用配置中的 CORS 来源
    cors_origins = config.get_cors_origins()

    # Flask-CORS 配置
    # 注意：当使用 supports_credentials=True 时，Access-Control-Allow-Origin 不能是 '*'
    # 必须使用具体的 origin 列表
    if cors_origins == ['*']:
        # 如果配置为 '*'，禁用 credentials 支持（因为 '*' 与 credentials 不兼容）
        log.warning("[CORS] CORS_ORIGINS 设置为 '*'，但应用需要 credentials 支持（JWT cookies）。"
                    "建议配置具体的 origins（如：CORS_ORIGINS=https://leo-zhao.natapp4.cc,http://localhost:5173）")
        CORS(app, supports_credentials=False, resources={r"/*": {"origins": "*"}})
        socketio_cors_origins = "*"
    else:
        # 使用具体的 origins 列表，支持 credentials
        log.info(f"[CORS] 配置允许的 origins: {cors_origins}, 启用 credentials 支持")
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
    from core.api.pic_routes import pic_bp
    from core.api.playlist_routes import playlist_bp
    from core.api.mi_routes import mi_bp
    from core.api.pdf_routes import pdf_bp
    from core.api.auth_routes import auth_bp
    from core.api.tts_routes import tts_bp
    from core.api.ai_routes import ai_bp

    app.register_blueprint(api_bp, url_prefix='/')
    app.register_blueprint(pic_bp, url_prefix='/pic')
    app.register_blueprint(agent_bp, url_prefix='/')
    app.register_blueprint(bluetooth_bp, url_prefix='/')
    app.register_blueprint(media_bp, url_prefix='/')
    app.register_blueprint(playlist_bp, url_prefix='/')
    app.register_blueprint(dlna_bp, url_prefix='/')
    app.register_blueprint(mi_bp, url_prefix='/')
    app.register_blueprint(pdf_bp, url_prefix='/')
    app.register_blueprint(auth_bp, url_prefix='/')
    app.register_blueprint(tts_bp, url_prefix='/')
    app.register_blueprint(ai_bp, url_prefix='/')

    # ========== JWT Auth ==========
    app.config['JWT_SECRET_KEY'] = config.JWT_SECRET_KEY
    app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=int(config.JWT_ACCESS_DAYS))
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=int(config.JWT_REFRESH_DAYS))

    # refresh token via HttpOnly cookie
    app.config['JWT_COOKIE_SECURE'] = bool(config.IS_PRODUCTION)
    app.config['JWT_COOKIE_SAMESITE'] = 'None'
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False
    app.config['JWT_REFRESH_COOKIE_PATH'] = '/api/auth/refresh'

    jwt = JWTManager(app)

    # token 无效（签名验证失败等）时返回 401，便于前端统一处理
    @jwt.invalid_token_loader
    def _invalid_token_callback(error_string: str):
        log.warning("[Auth] invalid token: %s", error_string)
        return jsonify({'code': -1, 'msg': 'token无效，请重新登录'}), 401

    # token 过期时返回 401
    @jwt.expired_token_loader
    def _expired_token_callback(jwt_header, jwt_payload):
        log.warning("[Auth] expired token")
        return jsonify({'code': -1, 'msg': 'token已过期，请重新登录'}), 401

    # flask-jwt-extended 4.x 要求 JWT 的 sub 为字符串，auth_routes 中 identity 为 dict，需序列化
    @jwt.user_identity_loader
    def _user_identity_loader(identity):
        if isinstance(identity, dict):
            return json.dumps(identity, sort_keys=True)
        return str(identity) if identity is not None else None

    def _parse_csv(raw: str) -> list[str]:
        return [x.strip() for x in (raw or '').split(',') if x.strip()]

    def _is_whitelisted(path: str) -> bool:
        # getAll 接口移出白名单，必须走 JWT 验证
        if path == '/getAll' or path.rstrip('/') == '/getAll':
            return False
        if not path.startswith('/api'):
            return True
        if config.AUTH_WHITELIST_ALL_API:
            return True
        if path.startswith('/api/auth/'):
            return True
        # pic 图片查看接口白名单（img 标签无法携带 JWT）
        if path.startswith('/api/pic/') or path.startswith('/pic/'):
            return True
        exact = set(_parse_csv(config.AUTH_API_WHITELIST))
        if path in exact:
            return True
        for p in _parse_csv(config.AUTH_API_WHITELIST_PREFIX):
            if path.startswith(p):
                return True
        return False

    @app.before_request
    def _auth_guard():
        path = request.path or ''
        if _is_whitelisted(path):
            return None
        has_auth_header = bool(request.headers.get('Authorization'))
        try:
            verify_jwt_in_request()
            return None
        except Exception as e:
            log.warning(
                "[Auth] 401 path=%s has_Authorization=%s err=%s",
                path,
                has_auth_header,
                type(e).__name__,
            )
            return jsonify({'code': -1, 'msg': 'unauthorized'}), 401

    @app.before_request
    def _record_start_time():
        """记录请求开始时间，用于计算响应时间"""
        request._start_time = time.time()

    @app.after_request
    def _log_access(response):
        """记录访问日志（仅在生产环境）"""
        if config.IS_PRODUCTION:
            # 获取请求信息
            method = request.method
            path = request.path
            status_code = response.status_code
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
            user_agent = request.headers.get('User-Agent', '-')

            # 计算响应时间
            if hasattr(request, '_start_time'):
                response_time = (time.time() - request._start_time) * 1000  # 转换为毫秒
            else:
                response_time = 0

            # 记录访问日志（格式：方法 路径 状态码 响应时间(ms) 客户端IP User-Agent）
            access_logger.info(f'{method} {path} {status_code} {response_time:.2f}ms {client_ip} {user_agent}')

        return response

    chat_mgr.init(socketio)
    db_mgr.init(app)
    ai_mgr.init()

    # 初始化定时任务调度器
    scheduler_mgr.start()
    return app


from core.models import *
