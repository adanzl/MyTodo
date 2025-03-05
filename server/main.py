import logging
from logging.handlers import TimedRotatingFileHandler

import core.ai.ai_mgr as ai_mgr
import core.db.db_mgr as db_mgr
from core.api.routes import api_bp
from core.chat.chat_mgr import ChatMgr

from app import app, socketio

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = TimedRotatingFileHandler('logs/app.log', when="midnight", backupCount=3, encoding="utf-8")
std_handler = logging.StreamHandler()
std_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[file_handler, std_handler])

log = logging.getLogger(__name__)

chat_mgr = ChatMgr()
db_mgr.init()
ai_mgr.init()

app.register_blueprint(api_bp, url_prefix='/')


@app.route("/")
def main():
    return "<p>Hello, World!</p>"


# . .venv/bin/activate
if __name__ == '__main__':
    #开始运行flask应用程序，以调试模式运行
    # app.run(debug=True, port=8888)
    socketio.run(app, debug=True, port=8000)
