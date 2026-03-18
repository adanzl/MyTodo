from __future__ import annotations

import json
import random
from collections import Counter
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
        执行一次抽奖。每次抽均发奖。
        当 t_user.wish_progress 达到配置阈值后，本抽仅从心愿单池抽取，抽完后 wish_progress 清零；否则从全池抽取。
        读取 category 的 count 字段，抽取 count 次，统一记录日志并返回。
        """
        # ========== 阶段 1：查询和校验 ==========
        user_data = self._db.get_data('t_user', user_id, "id,score,wish_progress,wish_list")
        if user_data['code'] != 0:
            return {"code": -1, "msg": "User not found"}

        ud = user_data['data']
        user_score = ud.get('score') or 0
        wish_progress = int(ud.get('wish_progress')) or 0
        wish_list_str = ud.get('wish_list') or '[]'

        # 获取抽奖配置
        cate_cost, wish_threshold, draw_count = self._get_cost_wish_threshold_and_count(cate_id)
        if cate_cost is None:
            return {
                "code": -1,
                "msg": "No lottery data" if cate_id == 0 else "Category not found",
            }

        # 校验积分（只扣一次费用）
        if user_score < cate_cost:
            return {"code": -1, "msg": "Not enough score"}

        # ========== 阶段 2：执行抽奖 ==========
        won_gifts = []
        cur_progress = wish_progress

        # 标记是否进行了心愿单抽奖（成功从心愿单抽中）
        has_wish_draw = False

        # 步骤 1：判断是否心愿单抽奖
        if wish_progress >= wish_threshold:
            # 步骤 1.1：拉取心愿单内可抽奖数据
            wish_pool = self._get_wish_pool(user_id, cate_id, wish_list_str)

            if wish_pool:
                # 抽 1 个心愿单奖品
                selected = random.choice(wish_pool)

                # 尝试扣减库存
                stock_success, need_remove = self._try_deduct_stock(selected['id'])

                if stock_success:
                    # 步骤 1.1.1：成功扣减
                    won_gifts.append(selected.copy())
                    cur_progress = 0  # 清空心愿单进度
                    has_wish_draw = True
                else:
                    # 步骤 1.1.2：不能成功扣减
                    pass

        # 步骤 2：普通抽奖（处理剩余次数）
        remaining_draws = draw_count - len(won_gifts)

        if remaining_draws > 0:
            full_pool = self._get_full_pool(cate_id)
            if not full_pool:
                return {"code": -1, "msg": "No available gifts"}

            # 用于记录需要排除的礼物 ID（库存为 0 或扣减失败的）
            excluded_ids = set()

            for _ in range(remaining_draws):
                # 过滤掉已排除的礼物
                available_pool = [g for g in full_pool if g['id'] not in excluded_ids]

                if not available_pool:
                    break  # 没有可用礼物了

                selected = random.choice(available_pool)

                # 尝试扣减库存
                stock_success, need_remove = self._try_deduct_stock(selected['id'])

                if stock_success:
                    won_gifts.append(selected.copy())

                    # 如果库存扣成 0，加入排除列表
                    if need_remove:
                        excluded_ids.add(selected['id'])
                else:
                    # 扣减失败，也加入排除列表
                    excluded_ids.add(selected['id'])

            # 普通抽奖完成后，心愿单进度 +1（只加 1 次，不是每次抽都加）
            # 只要没有从心愿单成功抽中，就算普通抽奖
            if not has_wish_draw:
                cur_progress = min(cur_progress + 1, wish_threshold)

        # 检查是否有中奖礼物
        if not won_gifts:
            return {"code": -1, "msg": "未能完成抽奖，奖品库存不足"}

        # ========== 阶段 3：写入日志 ==========
        out_key_str = ','.join(str(g['id']) for g in won_gifts)
        gift_info = ', '.join(f"[{g['id']}]{g['name']}" for g in won_gifts)

        add_ret = self._db.add_score(
            user_id,
            -cate_cost,  # 只扣一次费用
            'lottery',
            f"获得 {gift_info}",
            out_key=out_key_str,
        )

        if add_ret.get('code') != 0:
            log.error(f"写入积分历史失败：{add_ret.get('msg')}")
            return {"code": -1, "msg": f"写入积分历史失败：{add_ret.get('msg')}"}

        # ========== 阶段 4：更新用户状态 ==========
        self._db.set_data('t_user', {'id': user_id, 'wish_progress': cur_progress})

        # ========== 阶段 5：记录日志并返回 ==========
        log.info(f"Lottery success: user_id={user_id}, out_keys=[{out_key_str}], fee={cate_cost}")

        return {
            "code": 0,
            "msg": "抽奖成功",
            "data": {
                "gift": won_gifts[0] if won_gifts else None,  # 兼容旧客户端
                "gifts": won_gifts,
                "fee": cate_cost,  # 单次费用
                "single_fee": cate_cost,
                "count": len(won_gifts),
                "won": True,
            },
        }

    def _get_cost_wish_threshold_and_count(self, cate_id: int) -> tuple:
        """返回 (费用，心愿单满额阈值，抽取次数)。cate_id==0 从 rds lottery:2 读 fee、wish_count_threshold；否则从 t_gift_category 读 cost、count，阈值默认 5。"""
        default_threshold = 5
        default_count = 1
        if cate_id == 0:
            raw = self._rds.get_str("lottery:2")
            if not raw:
                return None, default_threshold, default_count
            try:
                cfg = json.loads(raw)
            except Exception:
                return None, default_threshold, default_count
            fee = cfg.get('fee')
            if fee is None:
                return None, default_threshold, default_count
            t = cfg.get('wish_count_threshold', default_threshold)
            t = max(1, int(t)) if isinstance(t, (int, float)) else default_threshold
            count = cfg.get('count', default_count)
            count = max(1, int(count)) if isinstance(count, (int, float)) else default_count
            return fee, t, count
        cat = self._db.get_data('t_gift_category', cate_id, "id,name,cost,count")
        if cat.get('code') != 0:
            return None, default_threshold, default_count
        cat_data = cat['data']
        count = cat_data.get('count', default_count)
        count = max(1, int(count)) if isinstance(count, (int, float)) else default_count
        return cat_data['cost'], default_threshold, count

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

    def _try_deduct_stock(self, gift_id: int) -> tuple[bool, bool]:
        """
        尝试扣减礼物库存，使用乐观锁 + 自旋重试机制。
            
        Args:
            gift_id: 礼物 ID
                
        Returns:
            (扣减是否成功，是否需要移除): 
            - 第一个 bool 表示扣减是否成功
            - 第二个 bool 表示扣减后库存是否为 0（需要移除）
        """
        max_retries = 30  # 最大重试次数
        retry_count = 0

        while retry_count < max_retries:
            try:
                # 获取最新的库存数据
                latest_data = self._db.get_data('t_gift', gift_id, 'id,stock')
                if latest_data.get('code') != 0 or not latest_data.get('data'):
                    log.error(f"获取礼物最新数据失败 [gift_id={gift_id}]")
                    return False, False

                latest_stock = latest_data['data'].get('stock')
                if not isinstance(latest_stock, (int, float)) or int(latest_stock) <= 0:
                    return False, True  # 库存不足，需要移除

                new_stock = int(latest_stock) - 1

                # 使用条件更新（乐观锁）：只有当 stock 未变时才更新成功
                update_data = {'id': gift_id, 'stock': new_stock}
                conditions = {'stock': latest_stock}  # CAS 条件

                update_ret = self._db.set_data('t_gift', update_data, conditions=conditions)

                if update_ret.get('code') == 0 and update_ret.get('cnt', 0) > 0:
                    # 更新成功
                    return True, (new_stock == 0)
                else:
                    # 更新失败（可能是并发冲突），重试
                    retry_count += 1
                    # 继续下一次重试
                    continue

            except Exception as e:
                log.error(f"扣减库存异常 [gift_id={gift_id}, retry={retry_count}]: {e}")
                retry_count += 1
        log.warning(f"扣减库存超过最大重试次数 [gift_id={gift_id}, retries={retry_count}]")

        return False, False

    def _commit_win(self, user_id: int, cate_cost: Any, gift: Dict[str, Any]) -> Dict[str, Any]:
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
            "data": {
                "gift": gift,
                "fee": cate_cost,
                "won": True
            },
        }

    def do_exchange(self, user_id: int, gift_id: int) -> Dict[str, Any]:
        """
        执行兑换：校验礼物可兑换且库存、用户积分足够，扣库存、扣积分并记录历史。
        """
        # 1. 查询礼物：需可兑换、有库存
        gift_res = self._db.get_data('t_gift', gift_id, '*')
        if gift_res.get('code') != 0:
            return {"code": -1, "msg": "礼物不存在"}
        gift = gift_res.get('data') or {}
        if not gift:
            return {"code": -1, "msg": "礼物不存在"}
        if (gift.get('exchange') or 0) != 1:
            return {"code": -1, "msg": "该奖品不可兑换"}
        stock = gift.get('stock')
        if not isinstance(stock, (int, float)) or int(stock) <= 0:
            return {"code": -1, "msg": "库存不足"}
        cost = gift.get('cost')
        if cost is None:
            cost = 0
        try:
            cost = int(cost)
        except (TypeError, ValueError):
            cost = 0
        if cost < 0:
            return {"code": -1, "msg": "无效的兑换积分"}

        # 2. 查询用户积分
        user_res = self._db.get_data('t_user', user_id, "id,score")
        if user_res.get('code') != 0:
            return {"code": -1, "msg": "用户不存在"}
        ud = user_res.get('data') or {}
        user_score = ud.get('score') or 0
        if user_score < cost:
            return {"code": -1, "msg": "积分不足"}

        # 3. 扣库存
        self._db.set_data('t_gift', {
            'id': gift_id,
            'stock': max(0,
                         int(stock) - 1),
        })

        # 4. 扣积分并记录历史
        add_ret = self._db.add_score(
            user_id,
            -cost,
            'exchange',
            f"兑换[{gift.get('id')}]{gift.get('name', '')}",
            out_key=gift_id,
        )
        if add_ret.get('code') != 0:
            return add_ret

        log.info(f"Exchange: user_id={user_id}, gift_id={gift_id}, cost={cost}")
        return {
            "code": 0,
            "msg": "兑换成功",
            "data": {
                "gift": gift,
                "cost": cost
            },
        }

    def undo_lottery(self, history_id: int) -> Dict[str, Any]:
        """
        撤销一次抽奖/兑换：删除该条积分历史、将用户积分恢复为操作前、对应礼物库存 +1。
        仅支持 action 为 lottery 或 exchange 且 out_key 有值的记录。
        """
        res = self._db.get_data('t_score_history', history_id, '*')
        if res.get('code') != 0:
            return {"code": -1, "msg": "查询历史记录失败"}
        rec = res.get('data') or {}
        if not rec:
            return {"code": -1, "msg": "历史记录不存在"}
        action = (rec.get('action') or '').strip()
        if action not in ('lottery', 'exchange'):
            return {"code": -1, "msg": "仅支持撤销抽奖/兑换记录"}
        out_key = rec.get('out_key')
        if out_key is None:
            return {"code": -1, "msg": "该记录无关联奖品，无法撤销"}
        user_id = rec.get('user_id')
        pre_value = rec.get('pre_value')
        if user_id is None or pre_value is None:
            return {"code": -1, "msg": "历史数据不完整"}

        # 恢复用户积分为抽奖前
        set_user = self._db.set_data('t_user', {'id': int(user_id), 'score': int(pre_value)})
        if set_user.get('code') != 0:
            return {"code": -1, "msg": "恢复积分失败"}

        # 礼物库存 +1（支持 out_key 为逗号分隔的多个礼物 id，包含重复 ID）
        out_key_str = str(out_key)
        gift_id_counts = Counter(
            int(part.strip()) for part in out_key_str.split(',') if part.strip() and part.strip().lstrip('-').isdigit())

        for gid, count in gift_id_counts.items():
            gift_res = self._db.get_data('t_gift', gid, 'id,stock')
            if gift_res.get('code') == 0 and gift_res.get('data'):
                g = gift_res['data']
                cur_stock = g.get('stock')
                if isinstance(cur_stock, (int, float)):
                    self._db.set_data('t_gift', {
                        'id': gid,
                        'stock': int(cur_stock) + count,
                    })

        # 删除积分历史
        del_res = self._db.del_data('t_score_history', history_id)
        if del_res.get('code') != 0:
            return {"code": -1, "msg": "删除历史记录失败"}

        log.info(f"Undo {action}: history_id={history_id}, user_id={user_id}, gift_id_counts={dict(gift_id_counts)}")
        return {"code": 0, "msg": "撤销成功", "data": {"user_id": user_id, "score": pre_value}}

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
        resp = self._db.get_list('t_gift', 1, 1000, ['cost', 'cate_id', 'stock'], conditions or None)

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
            cate_resp = self._db.get_list('t_gift_category', 1, 1000, ['id', 'name'], None)
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
        for cate_id, (cate_weighted, cate_stock) in sorted(by_cate.items(), key=_sort_key):
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
