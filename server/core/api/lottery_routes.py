"""抽奖/礼物相关 API 路由（lottery_mgr）。路径与 api_bp 同级，挂载在 / 下。"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from core.config import app_logger
from core.services.lottery_mgr import lottery_mgr
from core.utils import read_json_from_request
from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from core.services.stats_mgr import stats_mgr

log = app_logger
lottery_bp = Blueprint("lottery", __name__)


def _parse_int(
    value: Any,
    name: str,
) -> tuple[int, Optional[ResponseReturnValue]]:
    """把输入解析为 int。失败时返回错误响应。"""
    if value is None or value == "":
        return 0, {"code": -1, "msg": f"{name} is required"}
    try:
        return int(value), None
    except (TypeError, ValueError):
        return 0, {"code": -1, "msg": f"{name} must be int"}


@lottery_bp.route("/doLottery", methods=["POST"])
def do_lottery() -> ResponseReturnValue:
    """执行抽奖"""
    try:
        args: Dict[str, Any] = read_json_from_request()
        log.info("===== [Do Lottery] " + json.dumps(args))

        user_id_raw = args.get("user_id")
        pool_id_raw = args.get("pool_id")

        user_id, err = _parse_int(user_id_raw, "user_id")
        if err:
            return err

        pool_id, err = _parse_int(pool_id_raw, "pool_id")
        if err:
            return err

        return lottery_mgr.do_lottery(user_id, pool_id)
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": "error: " + str(e)}


@lottery_bp.route("/exchange", methods=["POST"])
def exchange() -> ResponseReturnValue:
    """执行兑换：扣库存、扣积分并记录历史。"""
    try:
        args: Dict[str, Any] = read_json_from_request()
        log.info("===== [Exchange] " + json.dumps(args))

        user_id_raw = args.get("user_id")
        gift_id_raw = args.get("gift_id")

        user_id, err = _parse_int(user_id_raw, "user_id")
        if err:
            return err

        gift_id, err = _parse_int(gift_id_raw, "gift_id")
        if err:
            return err

        return lottery_mgr.do_exchange(user_id, gift_id)
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": "error: " + str(e)}


@lottery_bp.route("/undoLottery", methods=["POST"])
def undo_lottery() -> ResponseReturnValue:
    """撤销一次抽奖：删除该条积分历史、恢复用户积分、补充对应礼物库存。"""
    try:
        args: Dict[str, Any] = read_json_from_request()
        history_id_raw = args.get("history_id")
        history_id, err = _parse_int(history_id_raw, "history_id")
        if err:
            return err
        return lottery_mgr.undo_lottery(history_id)
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": "error: " + str(e)}


@lottery_bp.route("/giftAvgCost", methods=["GET"])
def gift_avg_cost() -> ResponseReturnValue:
    """按 enable、exchange 筛选礼物并计算平均 cost。Query: enable, exchange（可选，整数）。"""
    try:
        raw_enable = request.args.get("enable", 1)
        raw_exchange = request.args.get("exchange")
        enable = int(raw_enable) if raw_enable not in (None, "") else None
        exchange_val = int(raw_exchange) if raw_exchange not in (None, "") else None
        return lottery_mgr.get_gift_avg_cost(enable=enable, exchange=exchange_val)
    except ValueError:
        return {"code": -1, "msg": "enable and exchange must be int"}
    except Exception as e:
        log.error(e)
        return {"code": -1, "msg": "error: " + str(e)}


@lottery_bp.route("/lottery/stats", methods=["GET"])
def get_lottery_stats() -> ResponseReturnValue:
    """获取用户统计数据"""
    try:
        user_id = request.args.get('user_id', type=str)
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)

        # 解析 user_id，支持单个ID或多个ID（逗号分隔）
        if user_id:
            user_ids = [int(uid.strip()) for uid in user_id.split(',') if uid.strip().isdigit()]
        else:
            user_ids = [3]

        # 多个用户，并行获取并合并结果
        results = []
        for uid in user_ids:
            result = stats_mgr.get_user_lottery_stats(uid, start_date, end_date)
            results.append({'user_id': uid, 'stats': result['stats'], 'categoryStats': result['categoryStats']})

        return {'code': 0, 'data': results}

    except Exception as e:
        log.error(e)
        return {'code': -1, 'msg': f'统计失败: {str(e)}'}
