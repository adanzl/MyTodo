from __future__ import annotations

import json
import random
from typing import Any, Dict

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
        """执行一次抽奖，返回与原 /doLottery 接口一致的结构。"""
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


lottery_mgr = LotteryMgr()

