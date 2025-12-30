from gevent import monkey
# 不 patch thread，使用真正的操作系统线程，避免与 asyncio 事件循环冲突
# thread=False 表示不 patch threading 模块，这样 ThreadPoolExecutor 会使用真正的线程
monkey.patch_all(subprocess=True, thread=False, queue=False)

# 在导入其他模块之前加载环境变量
from dotenv import load_dotenv
import os

# 加载 .env 文件
load_dotenv()

from flask import make_response
from core import create_app
from core.log_config import root_logger, access_logger

# 生产环境判断
IS_PRODUCTION = os.environ.get('ENV', 'development').lower() == 'production'

log = root_logger()

app = create_app()


@app.route("/")
def main():
    return "<p>Hello, World!</p>"


@app.after_request
def af_request(resp):
    """
    #请求钩子，在所有的请求发生后执行，加入headers。
    """
    resp = make_response(resp)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp


def null_application(environ, start_response):
    start_response("404 NOT FOUND", [("Content-Type", "text/plain")])
    yield b"NOT FOUND"


if __name__ == '__main__':
    import os

    # 支持环境变量配置
    PORT = int(os.environ.get('PORT', 8000))
    HOST = os.environ.get('HOST', '127.0.0.1')

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
            log=access_logger(),  # 使用访问日志记录器
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
