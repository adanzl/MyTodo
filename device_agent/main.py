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
