'''
媒体计划路由
'''
import json
from flask import Blueprint, request

from core.log_config import root_logger
from core.services.media_plan_mgr import media_plan_mgr
from core.utils import _ok, _err

log = root_logger()
media_plan_bp = Blueprint('media_plan', __name__)


# ========== 媒体计划接口 ==========

@media_plan_bp.route("/plan/get", methods=['GET'])
def plan_get():
    """
    获取当前存储的计划集合，支持通过 id 只返回单个计划
    """
    try:
        args = request.args
        plan_id = args.get("id")
        
        # 如果 id 为空、None 或空字符串，返回整个计划集合
        if plan_id is None or plan_id in ("None", "null", ""):
            ret = media_plan_mgr.get_plan(None)
        else:
            ret = media_plan_mgr.get_plan(plan_id)
            if not ret:
                return _err(f"未找到标识为 {plan_id} 的计划")
        return _ok(ret)
    except Exception as e:
        log.error(f"[MEDIA_PLAN] Get error: {e}")
        return _err(f'error: {str(e)}')


@media_plan_bp.route("/plan/update", methods=['POST'])
def plan_update():
    """
    更新单个计划
    传入单个计划数据，必须包含 id 字段
    """
    try:
        log.info("===== [Plan Update]")
        args = request.get_json(silent=True) or {}
        
        if not args:
            return _err("请求数据不能为空")
        
        plan_id = args.get("id")
        if not plan_id:
            return _err("计划 id 不能为空")
        
        ret = media_plan_mgr.update_single_plan(args)
        if ret != 0:
            return _err("更新计划失败")
        return _ok()
    except Exception as e:
        log.error(f"[MEDIA_PLAN] Update error: {e}")
        return _err(f'error: {str(e)}')


@media_plan_bp.route("/plan/updateAll", methods=['POST'])
def plan_update_all():
    """
    更新整个计划集合（覆盖）
    传入字典格式 {plan_id: plan_data, ...}
    """
    try:
        log.info("===== [Plan Update All]")
        args = request.get_json(silent=True) or {}
        
        if not args:
            return _err("请求数据不能为空")
        
        ret = media_plan_mgr.save_plan(args)
        if ret != 0:
            return _err("更新计划集合失败")
        return _ok()
    except Exception as e:
        log.error(f"[MEDIA_PLAN] UpdateAll error: {e}")
        return _err(f'error: {str(e)}')


@media_plan_bp.route("/plan/play", methods=['POST'])
def plan_play():
    """
    播放计划
    """
    try:
        args = request.get_json()
        id = args.get("id")
        force = args.get("force", False)
        if id is None:
            return _err("id is required")
        ret, msg = media_plan_mgr.play(id, force=force)
        if ret != 0:
            return _err(f"播放计划 {id} 失败: {msg}")
        return _ok()
    except Exception as e:
        log.error(f"[MEDIA_PLAN] Play error: {e}")
        return _err(f'error: {str(e)}')


@media_plan_bp.route("/plan/stop", methods=['POST'])
def plan_stop():
    """
    停止播放
    """
    try:
        args = request.get_json()
        id = args.get("id")
        if id is None:
            return _err("id is required")
        ret, msg = media_plan_mgr.stop(id)
        if ret != 0:
            return _err(f"停止播放失败: {msg}")
        return _ok()
    except Exception as e:
        log.error(f"[MEDIA_PLAN] Stop error: {e}")
        return _err(f'error: {str(e)}')


@media_plan_bp.route("/plan/reload", methods=['POST'])
def plan_reload():
    """
    重新从 RDS 中加载 plan 数据
    """
    try:
        log.info("===== [Plan Reload]")
        ret = media_plan_mgr.reload()
        if ret != 0:
            return _err("重新加载计划失败")
        return _ok()
    except Exception as e:
        log.error(f"[MEDIA_PLAN] Reload error: {e}")
        return _err(f'error: {str(e)}')
