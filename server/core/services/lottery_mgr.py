from __future__ import annotations

import json
import random
from typing import Any, Dict, Optional

import core.db.rds_mgr as rds_mgr
from core.config import app_logger
from core.db.db_mgr import db_mgr

log = app_logger


class LotteryMgr:
    """抽奖逻辑管理类，封装与用户积分、礼物池相关的业务规则。"""

    def __init__(self):
        self._db = db_mgr
        self._rds = rds_mgr

    def do_lottery(self, user_id: int, cate_id: int) -> Dict[str, Any]:
        """
        执行一次抽奖。每次抽中均发奖。
        当 t_user.wish_progress 达到配置阈值后，本抽仅从心愿单池抽取，抽完后 wish_progress 清零；否则从全池抽取。
        """
        # 1. 查询用户：积分 + 心愿单配置（t_user.wish_progress, wish_list）
        user_data = self._db.get_data(
            't_user', user_id, "id,score,wish_progress,wish_list"
        )
        if user_data['code'] != 0:
            return {"code": -1, "msg": "User not found"}

        ud = user_data['data']
        user_score = ud.get('score') or 0
        wish_progress = ud.get('wish_progress')
        if wish_progress is None:
            wish_progress = 0
        try:
            wish_progress = float(wish_progress)
        except (TypeError, ValueError):
            wish_progress = 0.0
        wish_list_str = ud.get('wish_list') or '[]'

        # 2. 获取抽奖费用；cate_id==0 时心愿单阈值从 rds 配置 lottery:2 读取
        cate_cost, wish_threshold = self._get_cost_and_wish_threshold(cate_id)
        if cate_cost is None:
            return {
                "code": -1,
                "msg": "No lottery data" if cate_id == 0 else "Category not found",
            }

        if user_score < cate_cost:
            return {"code": -1, "msg": "Not enough score"}

        # 3. 心愿单进度已满：优先从心愿单池抽，抽到则清零进度；心愿单为空则走普通抽奖且不重置进度
        if wish_progress >= wish_threshold:
            gifts = self._get_wish_pool(user_id, cate_id, wish_list_str)
            if not gifts:
                # 心愿单为空，普通抽奖，不重置心愿单进度
                gifts = self._get_full_pool(cate_id)
                if not gifts:
                    return {"code": -1, "msg": "No available gifts"}
                selected = random.choice(gifts)
                return self._commit_win(user_id, cate_cost, selected)
            selected = random.choice(gifts)
            self._db.set_data('t_user', {'id': user_id, 'wish_progress': 0})
            return self._commit_win(user_id, cate_cost, selected)

        # 4. 正常抽奖：全池抽取，抽中即发奖（无未中奖状态）
        gifts = self._get_full_pool(cate_id)
        if not gifts:
            return {"code": -1, "msg": "No available gifts"}
        selected = random.choice(gifts)
        return self._commit_win(user_id, cate_cost, selected)

    def _get_cost_and_wish_threshold(self, cate_id: int) -> tuple:
        """返回 (费用, 心愿单满额阈值)。cate_id==0 从 rds lottery:2 读 fee、wish_count_threshold；否则从 t_gift_category 读 cost，阈值默认 5。"""
        default_threshold = 5
        if cate_id == 0:
            raw = self._rds.get_str("lottery:2")
            if not raw:
                return None, default_threshold
            try:
                cfg = json.loads(raw)
            except Exception:
                return None, default_threshold
            fee = cfg.get('fee')
            if fee is None:
                return None, default_threshold
            t = cfg.get('wish_count_threshold', default_threshold)
            t = max(1, int(t)) if isinstance(t, (int, float)) else default_threshold
            return fee, t
        cat = self._db.get_data('t_gift_category', cate_id, "id,name,cost")
        if cat.get('code') != 0:
            return None, default_threshold
        return cat['data']['cost'], default_threshold

    def _parse_wish_list_ids(self, wish_list_str: str) -> list:
        """将 t_user.wish_list（JSON 数组字符串，如 '[1,2,3]'）解析为礼物 id 列表。"""
        if not wish_list_str or not wish_list_str.strip():
            return []
        try:
            arr = json.loads(wish_list_str)
        except Exception:
            return []
        if not isinstance(arr, list):
            return []
        return [int(x) for x in arr if isinstance(x, (int, float)) and int(x) == x]

    def _get_full_pool(self, cate_id: int) -> list:
        """获取当前分类下的全量可用奖池（enable=1, stock>0）。"""
        cond = {'enable': 1, 'stock': ('>', 0)}
        if cate_id != 0:
            cond['cate_id'] = cate_id
        res = self._db.get_list('t_gift', 1, 200, '*', cond)
        if res.get('code') != 0:
            return []
        return (res.get('data') or {}).get('data') or []

    def _get_wish_pool(self, user_id: int, cate_id: int, wish_list_str: str) -> list:
        """根据 t_user.wish_list 从全池中筛出用户心愿单内的可用礼物。"""
        ids = self._parse_wish_list_ids(wish_list_str)
        if not ids:
            return []
        full = self._get_full_pool(cate_id)
        return [g for g in full if g.get('id') in ids]

    def _commit_win(
        self, user_id: int, cate_cost: Any, gift: Dict[str, Any]
    ) -> Dict[str, Any]:
        """扣库存、扣积分并返回中奖结果。"""
        gid = gift.get('id')
        stock = gift.get('stock')
        if gid is not None and isinstance(stock, (int, float)):
            self._db.set_data('t_gift', {'id': gid, 'stock': max(0, int(stock) - 1)})
        self._db.add_score(
            user_id,
            -cate_cost,
            'lottery',
            f"获得[{gift.get('id')}]{gift.get('name', '')}",
            out_key=gift.get('id'),
        )
        log.info(f"Selected Gift: [{gift.get('id')}] {gift.get('name', '')}")
        return {
            "code": 0,
            "msg": "抽奖成功",
            "data": {"gift": gift, "fee": cate_cost, "won": True},
        }

    def get_gift_avg_cost(
        self,
        enable: Optional[int] = None,
        exchange: Optional[int] = None,
    ) -> Dict[str, Any]:
        """按 enable、exchange 筛选 t_gift，返回总均值与每个类别(cate_id)的均值。"""
        conditions: Dict[str, Any] = {}
        if enable is not None:
            conditions['enable'] = enable
        if exchange is not None:
            conditions['exchange'] = exchange
        resp = self._db.get_list(
            't_gift', 1, 1000, ['cost', 'cate_id', 'stock'], conditions or None
        )

        if resp.get('code') != 0:
            return {"code": -1, "msg": "Failed to query gift list"}

        data = resp.get('data') or {}
        gifts = data.get('data') or []

        weighted_sum = 0.0
        total_stock = 0
        by_cate: Dict[Any, tuple] = {}
        for g in gifts:
            c = g.get('cost')
            s = g.get('stock')
            if not isinstance(c, (int, float)) or not isinstance(s, (int, float)):
                continue
            cost_val = float(c) if isinstance(c, int) else c
            stock_val = int(s) if isinstance(s, float) else s
            if stock_val < 0:
                continue
            weighted_sum += cost_val * stock_val
            total_stock += stock_val
            cate_id = g.get('cate_id')
            if cate_id not in by_cate:
                by_cate[cate_id] = (0.0, 0)
            prev_w, prev_s = by_cate[cate_id]
            by_cate[cate_id] = (prev_w + cost_val * stock_val, prev_s + stock_val)

        cate_name_map: Dict[Any, str] = {}
        try:
            cate_resp = self._db.get_list('t_gift_category', 1, 1000,
                                          ['id', 'name'], None)
            if cate_resp.get('code') == 0:
                for c_row in (cate_resp.get('data') or {}).get('data') or []:
                    cid = c_row.get('id')
                    if cid is not None:
                        cate_name_map[cid] = c_row.get('name') or ''
        except Exception:
            pass

        if total_stock <= 0:
            return {"code": -1, "msg": "No matching gifts or zero total stock"}

        avg_cost = weighted_sum / total_stock

        def _sort_key(item: tuple) -> tuple:
            cid = item[0]
            return (cid is None, cid if cid is not None else 0)

        by_category = []
        for cate_id, (cate_weighted, cate_stock) in sorted(
            by_cate.items(), key=_sort_key
        ):
            cate_avg = cate_weighted / cate_stock if cate_stock > 0 else 0.0
            by_category.append({
                "cate_id": cate_id,
                "cate_name": cate_name_map.get(cate_id),
                "avg_cost": cate_avg,
                "count": cate_stock,
            })

        return {
            "code": 0,
            "msg": "ok",
            "data": {
                "avg_cost": avg_cost,
                "total_count": total_stock,
                "by_category": by_category,
            },
        }


lottery_mgr = LotteryMgr()
