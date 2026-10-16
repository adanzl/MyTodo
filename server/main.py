# --- 必须最先执行：gevent monkey patch -------------------------------------
# 放在任何 core.* 导入之前是**硬性要求**，原因：
#   `from core.config import ...` 会先导入父包 `core`，从而执行 core/__init__.py，
#   它连锁导入 rds_mgr（初始化时就会 ping Redis，建立真实 socket）、requests/
#   urllib3/aiohttp 等。若这些发生在 patch 之前：
#     - 连接池里会留下用标准库 socket 建立的连接，之后被 hub 复用时按阻塞方式读，
#       会占住整个 OS 线程；
#     - urllib3.util.ssl_ 等模块在导入时就绑定了未 patch 的 ssl，gevent 会发出
#       MonkeyPatchWarning（"may silently lead to incorrect behaviour"）。
# patch 的语义是替换 socket/ssl 等模块里的实现，已导入模块里早先绑定的引用不会
# 被追溯修改，所以顺序错了无法在事后补救。
from gevent import monkey
# 不 patch thread，使用真正的操作系统线程，避免与 asyncio 事件循环冲突
# thread=False 表示不 patch threading 模块，这样 ThreadPoolExecutor 会使用真正的线程
# queue=False 让 queue.Queue 保持原生实现，供 core/tools/hub_dispatch.py 跨线程投递
# subprocess=True 表示 patch subprocess 模块，避免 gevent subprocess 在新线程中的
# "child watchers are only available on the default loop" 错误
monkey.patch_all(subprocess=True, thread=False, queue=False)

import os

from dotenv import load_dotenv

load_dotenv()

from core.config import _SERVER_ROOT

# 规范运行目录：统一切换到 server 根目录，使相对路径（如 DEFAULT_BASE_DIR=data）解析一致
os.chdir(_SERVER_ROOT)

from flask import make_response
from core import create_app
from core.config import app_logger, config, gevent_access_logger

# 让真实线程（ASR/TTS 的 ws 线程）能把回调交回 hub 执行，见 core/tools/hub_dispatch.py
from core.tools.hub_dispatch import start_hub_drain

# 生产环境判断
IS_PRODUCTION = config.IS_PRODUCTION

log = app_logger

app = create_app()

# 在 hub（此处即主线程）上启动投递消费循环：
# 真实线程通过 post_to_hub 投递的回调将由 hub 的 greenlet 执行。
start_hub_drain()


@app.route("/")
def main():
    return "<p>Hello, World!</p>"


@app.route("/health")
def health():
    return {"status": "ok"}


def null_application(environ, start_response):
    if environ.get("PATH_INFO") == "/health":
        start_response("200 OK", [("Content-Type", "application/json")])
        yield b"{\"status\":\"ok\"}"
        return
    start_response("404 NOT FOUND", [("Content-Type", "text/plain")])
    yield b"NOT FOUND"


if __name__ == '__main__':
    # 支持统一配置
    PORT = config.PORT
    HOST = config.HOST

    # 只在开发环境禁用浏览器缓存
    if not IS_PRODUCTION:

        @app.after_request
        def disable_cache(resp):
            resp = make_response(resp)
            resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            resp.headers['Pragma'] = 'no-cache'
            resp.headers['Expires'] = '0'
            return resp

    try:
        from werkzeug.middleware.dispatcher import DispatcherMiddleware
        from werkzeug.middleware.shared_data import SharedDataMiddleware
        from gevent.pywsgi import WSGIServer
        from geventwebsocket.handler import WebSocketHandler

        base_dir = os.path.dirname(os.path.abspath(__file__))
        static_app = SharedDataMiddleware(null_application, {'/': 'static'})
        application = DispatcherMiddleware(
            null_application,  # 主应用（此处为空）
            {
                '/api': app,
                '/web': static_app,  # 静态文件挂载到 /web
            })
        http_server = WSGIServer(
            (HOST, PORT),
            application,
            log=gevent_access_logger,  # 使用 gevent.access 记录器
            error_log=log,  # 错误日志使用应用日志
            handler_class=WebSocketHandler,
        )
        env_info = 'production' if IS_PRODUCTION else 'development'
        log.info(f'Server started on http://{HOST}:{PORT} (using gevent, env={env_info})')
        http_server.serve_forever()
    except ImportError as e:
        log.error(f'Gevent 相关模块导入失败: {e}')
        log.error('请运行: pip install gevent gevent-websocket')
        log.info('尝试使用 Flask 开发服务器...')
        app.run(host=HOST, port=PORT, debug=False)
    except Exception as e:
        log.error(f'启动服务器失败: {e}')
        log.info('尝试使用 Flask 开发服务器...')
        app.run(host=HOST, port=PORT, debug=False)
