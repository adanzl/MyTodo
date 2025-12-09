from flask import make_response
from gevent import monkey

# 排除 threading 模块，避免影响 pynput 的线程操作
monkey.patch_all(subprocess=True, thread=False)  # 不 patch thread，避免影响 pynput
from core import create_app
from core.log_config import root_logger

log = root_logger()

app, socketio = create_app()


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
    PORT = 8001
    HOST = '127.0.0.1'
    
    log.info(f"启动服务在 http://{HOST}:{PORT}")
    socketio.run(app, host=HOST, port=PORT, debug=False)