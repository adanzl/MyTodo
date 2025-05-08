from flask import Response
from core.log_config import root_logger

log = root_logger()


def default_app(env, resp):
    return Response("Not Found", status=404)


def null_application(environ, start_response):
    start_response("404 NOT FOUND", [("Content-Type", "text/plain")])
    yield b"NOT FOUND"


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    import os
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from werkzeug.middleware.shared_data import SharedDataMiddleware
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))  # 假设代码文件在项目根目录
        print(os.path.join(base_dir, 'static'))
        static_app = SharedDataMiddleware(null_application, {'/': os.path.join(base_dir, 'static')})

        application = DispatcherMiddleware(
            None,
            {
                '/web': static_app,  # 静态文件挂载到 /web
            })
        run_simple('localhost', 8000, application, use_reloader=True, use_debugger=True, reloader_type='stat')
    except Exception as e:
        log.error(e)
