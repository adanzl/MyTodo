from core.log_config import root_logger
from flask import Blueprint, render_template

log = root_logger()
api_bp = Blueprint('api', __name__)


@api_bp.route("/log")
def server_log():
    with open("logs/app.log", "r") as f:
        # 读取文件所有行
        lines = f.readlines()
        # 反转行的顺序
        lines.reverse()
        log_content = ''.join(lines)
    return render_template('server_log.html', log_content=log_content)
