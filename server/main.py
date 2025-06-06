import core.ai.ai_mgr as ai_mgr
import core.db.db_mgr as db_mgr
from app import app, socketio
from core.chat.ai_chat_mgr import ChatMgr
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
    from werkzeug.serving import run_simple
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from werkzeug.middleware.shared_data import SharedDataMiddleware
    import os
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))  # 假设代码文件在项目根目录
        static_app = SharedDataMiddleware(null_application, {'/': 'static'})
        application = DispatcherMiddleware(
            null_application,  # 主应用（此处为空）
            {
                '/api': app,
                '/web': static_app,  # 静态文件挂载到 /web
            })
        js_files = [os.path.join('static', f) for f in os.listdir('static') if f.endswith('.js') or f.endswith('.html')]
        run_simple(
            'localhost',
            8000,
            application,
            use_reloader=True,
            use_debugger=True,
            threaded=False,  # 禁用多线程
            processes=1,  # 禁用多进程
            reloader_type='stat',
            extra_files=js_files)
    except Exception as e:
        log.error(e)
