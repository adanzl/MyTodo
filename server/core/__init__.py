from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

import core.ai.ai_mgr as ai_mgr
from core.api.routes import api_bp
from core.api.bluetooth_routes import bluetooth_bp
from core.api.dlna_routes import dlna_bp
from core.api.media_routes import media_bp
from core.chat.chat_mgr import ChatMgr
from core.db.db_mgr import DB_Mgr
from core.scheduler import init_scheduler
import os
import asyncio


def run_async(coro, timeout: float = None):
    """
    在新的事件循环中运行协程
    用于在同步代码中调用异步函数
    
    :param coro: 协程对象
    :param timeout: 超时时间（秒），可选
    :return: 协程的返回值
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if timeout:
            return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
        else:
            return loop.run_until_complete(coro)
    except asyncio.TimeoutError:
        raise
    finally:
        try:
            # 取消所有待处理的任务
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            loop.close()
            asyncio.set_event_loop(None)


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
    app.register_blueprint(bluetooth_bp, url_prefix='/')
    app.register_blueprint(media_bp, url_prefix='/')
    app.register_blueprint(dlna_bp, url_prefix='/')

    ChatMgr(socketio)
    DB_Mgr.init(app)
    ai_mgr.init()

    # 初始化定时任务调度器
    init_scheduler()

    return app


from core.models import *
