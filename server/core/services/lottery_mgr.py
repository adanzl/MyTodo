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
        # 目前直接复用全局的 db_mgr / rds_mgr，如果后续需要可以改为依赖注入
        self._db = db_mgr
        self._rds = rds_mgr

    def do_lottery(self, user_id: int, cate_id: int) -> Dict[str, Any]:
        """执行一次抽奖"""
        # 查询用户积分
        user_data = self._db.get_data('t_user', user_id, "id,score")
        if user_data['code'] != 0:
            return {"code": -1, "msg": "User not found"}

        user_score = user_data['data']['score']

        # 根据 cate_id 获取抽奖类别费用
        if cate_id == 0:
            # cate_id 为 0 时，从 Redis 中读取配置
            key = "lottery:2"
            cate_data_str = self._rds.get_str(key)
            if not cate_data_str:
                return {"code": -1, "msg": "No lottery data"}

            try:
                cate_json = json.loads(cate_data_str)
            except Exception:
                return {"code": -1, "msg": "No lottery data"}

            cate_cost = cate_json.get('fee')
            if cate_cost is None:
                return {"code": -1, "msg": "No lottery data"}
        else:
            # cate_id 非 0 时，从数据库的礼物分类表读取
            cate_data = self._db.get_data('t_gift_category', cate_id,
                                          "id,name,cost")
            if cate_data['code'] != 0:
                return {"code": -1, "msg": "Category not found"}
            cate_cost = cate_data['data']['cost']

        # 积分不足
        if user_score < cate_cost:
            return {"code": -1, "msg": "Not enough score"}

        # 构造礼物候选池（仅查 enable=1 且 stock>0）
        conditions = {'enable': 1, 'stock': ('>', 0)}
        if cate_id != 0:
            conditions['cate_id'] = cate_id
        lottery_poll = self._db.get_list('t_gift', 1, 200, '*', conditions)

        if lottery_poll['code'] != 0 or not lottery_poll['data'][
                'data'] or len(lottery_poll['data']['data']) == 0:
            return {"code": -1, "msg": "No available gifts"}

        gifts = lottery_poll['data']['data']
        selected_gift = random.choice(gifts)

        log.info(
            f"Selected Gift: [{selected_gift['id']}] {selected_gift.get('name', '')}"
        )

        if not selected_gift:
            return {"code": -1, "msg": "Lottery failed"}

        # 中奖后扣减库存（stock）
        gift_id = selected_gift.get('id')
        stock = selected_gift.get('stock')
        if gift_id is not None and isinstance(stock, (int, float)):
            new_stock = int(stock) - 1
            if new_stock < 0:
                new_stock = 0
            # 只更新 id 与 stock 字段，其它字段保持不变
            self._db.set_data('t_gift', {
                'id': gift_id,
                'stock': new_stock,
            })

        # 扣除积分并记录积分变更历史
        self._db.add_score(
            user_id,
            -cate_cost,
            'lottery',
            f"获得[{selected_gift['id']}]{selected_gift.get('name', '')}",
            out_key=selected_gift['id'],
        )

        return {
            "code": 0,
            "msg": "抽奖成功",
            "data": {
                "gift": selected_gift,
                "fee": cate_cost
            }
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

        # 按库存加权：(cost, stock) 列表；总加权和与总库存
        weighted_sum = 0.0
        total_stock = 0
        # 按 cate_id 分组：(cost*stock 累加, stock 累加)
        by_cate: Dict[Any, tuple] = {}  # cate_id -> (sum_cost_stock, sum_stock)
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

        # 查询类别名称映射（t_gift_category.id -> name）
        cate_name_map: Dict[Any, str] = {}
        try:
            cate_resp = self._db.get_list('t_gift_category', 1, 1000,
                                          ['id', 'name'], None)
            if cate_resp.get('code') == 0:
                cate_data = cate_resp.get('data') or {}
                cate_list = cate_data.get('data') or []
                for c_row in cate_list:
                    cid = c_row.get('id')
                    if cid is not None:
                        cate_name_map[cid] = c_row.get('name') or ''
        except Exception:
            # 分类名称获取失败时，不影响均值计算，只是不返回名称
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

