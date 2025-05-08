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


# . .venv/bin/activate
if __name__ == '__main__':
    # app.run(debug=True, port=8888)
    from werkzeug.serving import run_simple
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from werkzeug.middleware.shared_data import SharedDataMiddleware
    try:
        static_app = SharedDataMiddleware(None, {'/': 'static'})
        application = DispatcherMiddleware(
            None,  # 主应用（此处为空）
            {
                '/api': app,
                '/web': static_app,  # 静态文件挂载到 /web
            })
        run_simple('localhost', 8000, application, use_reloader=True, use_debugger=True, reloader_type='stat')
        # socketio.run(app, debug=True, port=8000)
    except Exception as e:
        log.error(e)
