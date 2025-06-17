from gevent import monkey

monkey.patch_all()  # 在导入其他模块之前进行 patch
import core.ai.ai_mgr as ai_mgr
import core.db.db_mgr as db_mgr
from app import app, socketio
from core.chat.chat_mgr import ChatMgr
from core.log_config import root_logger

log = root_logger()

chat_mgr = ChatMgr()
db_mgr.init()
ai_mgr.init()


@app.route("/")
def main():
    return "<p>Hello, World!</p>"


def null_application(environ, start_response):
    start_response("404 NOT FOUND", [("Content-Type", "text/plain")])
    yield b"NOT FOUND"


if __name__ == '__main__':
    import os

    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from werkzeug.middleware.shared_data import SharedDataMiddleware
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))  # 假设代码文件在项目根目录
        static_app = SharedDataMiddleware(null_application, {'/': 'static'})
        application = DispatcherMiddleware(
            null_application,  # 主应用（此处为空）
            {
                '/api': app,
                '/web': static_app,  # 静态文件挂载到 /web
            })
        # 使用 gevent 的 WSGI 服务器
        from gevent.pywsgi import WSGIServer
        from geventwebsocket.handler import WebSocketHandler  # 添加这行

        # SSL 证书路径
        http_server = WSGIServer(
            ('127.0.0.1', 8000),
            application,
            handler_class=WebSocketHandler,
        )
        print('Server started on http://0.0.0.0:8000')
        http_server.serve_forever()
    except Exception as e:
        log.error(e)
