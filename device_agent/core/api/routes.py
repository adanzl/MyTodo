from core.log_config import root_logger
from core.scheduler import get_scheduler
from core.config import get_config
from flask import Blueprint, json, jsonify, render_template, request

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


@api_bp.route("/cron/status")
def cron_status():
    """获取定时任务状态"""
    try:
        scheduler = get_scheduler()
        status = scheduler.get_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        log.error(f"获取定时任务状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route("/cron/update", methods=['POST'])
def cron_update():
    """更新定时任务配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请提供配置数据'
            }), 400
        
        config = get_config()
        
        # 获取参数
        enabled = data.get('enabled')
        expression = data.get('expression')
        command = data.get('command')
        duration = data.get('duration')
        
        # 验证参数
        if enabled is not None and not isinstance(enabled, bool):
            return jsonify({
                'success': False,
                'error': 'enabled 参数必须是布尔值'
            }), 400
        
        # 如果提供了 expression，验证格式
        if expression is not None:
            parts = expression.strip().split()
            if len(parts) != 5:
                return jsonify({
                    'success': False,
                    'error': 'cron 表达式格式错误，应为 5 个字段（分 时 日 月 周）'
                }), 400
        
        # 如果提供了 duration，验证格式
        if duration is not None:
            if not isinstance(duration, int) or duration < 0:
                return jsonify({
                    'success': False,
                    'error': 'duration 必须是非负整数（秒）'
                }), 400
        
        # 更新配置
        success = config.update_cron_config(
            enabled=enabled,
            expression=expression,
            command=command,
            duration=duration
        )
        
        if not success:
            return jsonify({
                'success': False,
                'error': '保存配置失败'
            }), 500
        
        # 重启调度器以应用新配置
        try:
            scheduler = get_scheduler()
            scheduler.restart()
            log.info("定时任务配置已更新并重启")
        except Exception as e:
            log.error(f"重启调度器失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'配置已保存，但重启调度器失败: {str(e)}'
            }), 500
        
        # 返回更新后的状态
        status = scheduler.get_status()
        return jsonify({
            'success': True,
            'message': '配置已更新',
            'data': status
        })
        
    except Exception as e:
        log.error(f"更新定时任务配置失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
