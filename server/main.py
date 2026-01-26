from dotenv import load_dotenv

load_dotenv()

from gevent import monkey
# 不 patch thread，使用真正的操作系统线程，避免与 asyncio 事件循环冲突
# thread=False 表示不 patch threading 模块，这样 ThreadPoolExecutor 会使用真正的线程
# subprocess=False 表示不 patch subprocess 模块，避免 gevent subprocess 在新线程中的 "child watchers are only available on the default loop" 错误
# 当 subprocess=False 时，标准库的 subprocess 在 gevent 环境中可能无法正常工作（因为 gevent 已 patch 了 socket、select 等）
monkey.patch_all(subprocess=True, thread=False, queue=False)

import os

from aliyun.opentelemetry.instrumentation.auto_instrumentation import sitecustomize

from flask import make_response
from core import create_app
from core.config import app_logger, config, gevent_access_logger

# 生产环境判断
IS_PRODUCTION = config.IS_PRODUCTION

log = app_logger

app = create_app()


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
