from flask import make_response
from gevent import monkey

monkey.patch_all(subprocess=True)  # 在导入其他模块之前进行 patch，包括 subprocess
from core import create_app
from core.log_config import root_logger

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

    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from werkzeug.middleware.shared_data import SharedDataMiddleware
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        static_app = SharedDataMiddleware(null_application, {'/': 'static'})
        application = DispatcherMiddleware(
            null_application,  # 主应用（此处为空）
            {
                '/api': app,
                '/web': static_app,  # 静态文件挂载到 /web
            })
        from gevent.pywsgi import WSGIServer
        from geventwebsocket.handler import WebSocketHandler
        PORT = 8000
        HOST = '127.0.0.1'
        http_server = WSGIServer(
            (HOST, PORT),
            application,
            log=None,
            handler_class=WebSocketHandler,
        )
        log.info(f'Server started on http://{HOST}:{PORT}')
        http_server.serve_forever()
    except Exception as e:
        log.error(e)
