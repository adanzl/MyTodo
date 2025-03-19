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
    #开始运行flask应用程序，以调试模式运行
    # app.run(debug=True, port=8888)
    try:
        socketio.run(app, debug=True, port=8000)
    except Exception as e:
        log.error(e)
