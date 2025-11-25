import os
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from core.api.routes import api_bp
from core.api.bluetooth_routes import bluetooth_bp
from core.api.media_routes import media_bp
from core.scheduler import get_scheduler
from core.log_config import root_logger

log = root_logger()

def create_app():
    instance_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 明确指定 template_folder 路径
    template_folder = os.path.join(instance_path, 'templates')
    app = Flask(__name__, 
                instance_path=instance_path, 
                instance_relative_config=True,
                template_folder=template_folder)
    
    # 配置 JSON 返回时不转义中文字符
    app.config['JSON_AS_ASCII'] = False

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

    # 启动定时任务调度器
    try:
        scheduler = get_scheduler()
        scheduler.start()
        log.info("定时任务调度器初始化完成")
    except Exception as e:
        log.error(f"定时任务调度器启动失败: {str(e)}")

    return app
