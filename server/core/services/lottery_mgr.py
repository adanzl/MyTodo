from __future__ import annotations

import json
import random
from collections import Counter
from typing import Any, Dict, List, Optional

import core.db.rds_mgr as rds_mgr
from core.config import app_logger
from core.db.db_mgr import db_mgr
from core.utils import fmt_ts

log = app_logger


def _err(msg: str) -> Dict[str, Any]:
    return {"code": -1, "msg": msg}


def _row(table: str, row_id: int, fields: str = '*') -> Optional[Dict[str, Any]]:
    res = db_mgr.get_data(table, row_id, fields)
    if res.get('code') != 0:
        return None
    return res.get('data') or None


def _as_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


class LotteryMgr:
    """抽奖逻辑管理类，封装与用户积分、礼物池相关的业务规则。"""

    def _fetch_gifts(self, extra: Optional[Dict[str, Any]] = None, limit: int = 500) -> list:
        """根据分类 ID 列表或心愿单 ID 等条件，获取 enable=1 且 stock>0 的可用奖池。"""
        cond: Dict[str, Any] = {'enable': 1, 'stock': {'>': 0}}
        if extra:
            cond.update(extra)
        res = db_mgr.get_list('t_gift', 1, limit, '*', cond)
        if res.get('code') != 0:
            return []
        return (res.get('data') or {}).get('data') or []

    def _write_gift_history(
        self,
        user_id: int,
        gifts: List[Dict[str, Any]],
        *,
        pool_id: Optional[int],
        msg: str,
    ) -> None:
        """写入 t_gift_history 礼物记录（抽奖/兑换各一条）。"""
        for gift in gifts:
            gift_id = gift.get('id')
            if gift_id is None:
                continue
            ret = db_mgr.set_data('t_gift_history', {
                'gift_id': int(gift_id),
                'gift_name': gift.get('name') or '',
                'user_id': user_id,
                'gift_cate_id': gift.get('cate_id'),
                'gift_pool_id': pool_id,
                'status': 1,
                'wish': 1 if gift.get('_from_wish') else 0,
                'msg': msg,
                'dt': fmt_ts(),
            })
            if ret.get('code') != 0:
                log.error(f"写入礼物历史失败 [user_id={user_id}, gift_id={gift_id}]: {ret.get('msg')}")

    def do_lottery(self, user_id: int, pool_id: int) -> Dict[str, Any]:
        """
        执行一次抽奖。每次抽均发奖。
        当 t_user.wish_progress 达到配置阈值后，本抽仅从心愿单池抽取，抽完后 wish_progress 清零；否则从全池抽取。
        读取 pool 的 cate_list 字段获取分类 ID 列表，从这些分类中抽取礼物，抽取 count 次，统一记录日志并返回。
        """
        # ========== 阶段 1：查询和校验 ==========
        ud = _row('t_user', user_id, "id,score,wish_progress,wish_list,inventory")
        if not ud:
            return _err("User not found")

        user_score = ud.get('score') or 0
        wish_progress = _as_int(ud.get('wish_progress'))
        wish_list_str = ud.get('wish_list') or '[]'

        # 获取奖池配置（从 t_gift_pool 获取）
        pool_cost, wish_threshold, draw_count, cate_ids = self._get_pool_config(pool_id)
        if pool_cost is None:
            return _err("No lottery data" if pool_id == 0 else "Pool not found")
        # 校验积分（只扣一次费用）
        if user_score < pool_cost:
            return _err("Not enough score")

        # ========== 阶段 2：执行抽奖 ==========
        log.info(f"Do lottery, user: {user_id}, pool: {pool_id}, categories: {cate_ids}")
        won_gifts: List[Dict[str, Any]] = []
        cur_progress = wish_progress

        # 标记是否进行了心愿单抽奖（成功从心愿单抽中）
        has_wish_draw = False

        # 步骤 1：判断是否心愿单抽奖
        if wish_progress >= wish_threshold:
            # 步骤 1.1：拉取心愿单内可抽奖数据
            # 将 t_user.wish_list（JSON 数组字符串，如 '[1,2,3]'）解析为礼物 id 列表
            wish_ids: List[int] = []
            if wish_list_str.strip():
                try:
                    arr = json.loads(wish_list_str)
                    if isinstance(arr, list):
                        wish_ids = [int(x) for x in arr if isinstance(x, (int, float)) and int(x) == x]
                except Exception:
                    pass
            wish_pool = self._fetch_gifts({'id': {'in': wish_ids}}, limit=len(wish_ids)) if wish_ids else []
            if wish_pool:
                # 从心愿单中随机选择一个（心愿单内不使用加权）
                selected = random.choice(wish_pool)
                # 尝试扣减库存
                stock_success, _ = self._try_deduct_stock(selected['id'])
                if stock_success:
                    # 步骤 1.1.1：成功扣减
                    selected_copy = selected.copy()
                    selected_copy['_from_wish'] = True  # 标记为心愿单礼物
                    won_gifts.append(selected_copy)
                    cur_progress = 0  # 清空心愿单进度
                    has_wish_draw = True
                else:
                    # 步骤 1.1.2：不能成功扣减
                    pass

        # 步骤 2：普通抽奖（处理剩余次数）
        remaining_draws = draw_count - len(won_gifts)
        if remaining_draws > 0:
            extra = {'cate_id': {'in': cate_ids}} if cate_ids else None
            full_pool = self._fetch_gifts(extra)
            if not full_pool:
                return _err("No available gifts")

            # 用于记录需要排除的礼物 ID（库存为 0 或扣减失败的）
            excluded_ids: set = set()
            for _ in range(remaining_draws):
                # 过滤掉已排除的礼物
                available_pool = [g for g in full_pool if g['id'] not in excluded_ids]
                if not available_pool:
                    break  # 没有可用礼物了

                # 使用 weighted_random_choice：根据物品库存数量作为权重进行加权随机选择
                weights = [max(1, _as_int(g.get('stock'), 1)) for g in available_pool]
                selected = random.choices(available_pool, weights=weights, k=1)[0]

                # 尝试扣减库存
                stock_success, need_remove = self._try_deduct_stock(selected['id'])
                if stock_success:
                    selected_copy = selected.copy()
                    selected_copy['_from_wish'] = False  # 标记为普通礼物
                    won_gifts.append(selected_copy)
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
            return _err("未能完成抽奖，奖品库存不足")

        # ========== 阶段 3：写入日志 ==========
        out_key_str = ','.join(str(g['id']) for g in won_gifts)

        # 在心愿单礼物名字前加 * 标记
        gift_info = ', '.join(
            f"[{g['id']}]{'*' if g.get('_from_wish') else ''}{g['name']}" for g in won_gifts
        )

        add_ret = db_mgr.add_score(
            user_id,
            -pool_cost,  # 只扣一次费用
            'lottery',
            f"获得 {gift_info}",
            out_key=out_key_str,
        )
        if add_ret.get('code') != 0:
            log.error(f"写入积分历史失败：{add_ret.get('msg')}")
            return _err(f"写入积分历史失败：{add_ret.get('msg')}")

        grant_msg = f"费用{pool_cost}，获得 {gift_info}"
        self._write_gift_history(user_id, won_gifts, pool_id=pool_id, msg=grant_msg)

        # ========== 阶段 4：更新用户状态 ==========
        log.info(
            f"Update wish_progress: user_id={user_id}, old={wish_progress}, "
            f"new={cur_progress}, wish_list={wish_list_str}"
        )
        inv = json.loads(ud.get('inventory') or '{}')
        for g in won_gifts:
            if g.get('cate_id') is not None:
                k = str(int(g['cate_id']))
                inv[k] = inv.get(k, 0) + 1
        if db_mgr.set_data('t_user', {
            'id': user_id,
            'inventory': json.dumps(inv),
            'wish_progress': cur_progress,
        }).get('code') != 0:
            return _err("更新用户数据失败")

        # ========== 阶段 5：记录日志并返回 ==========
        log.info(
            f"Lottery success: user_id={user_id}, out_keys=[{out_key_str}], "
            f"fee={pool_cost}, wish_draw={has_wish_draw}"
        )

        return {
            "code": 0,
            "msg": "抽奖成功",
            "data": {
                "gift": won_gifts[0],  # 兼容旧客户端
                "gifts": won_gifts,
                "fee": pool_cost,  # 单次费用
                "single_fee": pool_cost,
                "count": len(won_gifts),
                "won": True,
            },
        }

    def _get_pool_config(self, pool_id: int) -> tuple:
        """
        返回 (费用，心愿单满额阈值，抽取次数，分类 ID 列表)。
        从 rds lottery:2 读 fee、wish_count_threshold；
        从 t_gift_pool 读 cost、count、cate_list。
        Args:
            pool_id: int - 奖池 ID

        Returns:
            tuple: (费用，心愿单满额阈值，抽取次数，分类 ID 列表)
        """
        default_threshold = 5
        default_count = 1
        fail = (None, default_threshold, default_count, [])

        # 从 Redis 读取全局配置（fee 和 wish_count_threshold）
        raw = rds_mgr.get_str("lottery:2")
        if not raw:
            return fail
        try:
            cfg = json.loads(raw)
        except Exception:
            return fail

        # 获取心愿单阈值（所有奖池共用）
        wish_threshold = max(1, _as_int(cfg.get('wish_count_threshold'), default_threshold))

        if pool_id == 0:
            # pool_id==0 时使用 Redis 中的 fee
            if cfg.get('fee') is None:
                return fail
            return _as_int(cfg['fee']), wish_threshold, max(1, _as_int(cfg.get('count'), default_count)), []

        # 从数据库读取奖池配置
        pool_data = _row('t_gift_pool', pool_id, "id,name,cost,count,count_mx,cate_list")
        if not pool_data:
            # 奖池不存在
            return fail

        # 获取 count 和 count_mx，生成随机抽取次数
        count_min = max(1, _as_int(pool_data.get('count'), default_count))
        count_mx = max(count_min, _as_int(pool_data.get('count_mx'), count_min))

        # 在 count 到 count_mx 之间随机选择一个抽取次数
        draw_count = random.randint(count_min, count_mx)

        # 解析 cate_list 字段（逗号分隔的字符串）为分类 ID 列表
        cate_list_str = (pool_data.get('cate_list') or '').strip()
        cate_ids = [
            int(x.strip()) for x in cate_list_str.split(',')
            if x.strip().lstrip('-').isdigit()
        ] if cate_list_str else []

        return pool_data['cost'], wish_threshold, draw_count, cate_ids

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
        for retry_count in range(max_retries):
            try:
                # 获取最新的库存数据
                latest = _row('t_gift', gift_id, 'id,stock')
                if not latest:
                    log.error(f"获取礼物最新数据失败 [gift_id={gift_id}]")
                    return False, False

                latest_stock = latest.get('stock')
                if not isinstance(latest_stock, (int, float)) or int(latest_stock) <= 0:
                    return False, True  # 库存不足，需要移除

                new_stock = int(latest_stock) - 1

                # 使用条件更新（乐观锁）：只有当 stock 未变时才更新成功
                update_ret = db_mgr.set_data(
                    't_gift',
                    {'id': gift_id, 'stock': new_stock},
                    conditions={'stock': latest_stock},
                )
                if update_ret.get('code') == 0 and update_ret.get('cnt', 0) > 0:
                    # 更新成功
                    return True, new_stock == 0
            except Exception as e:
                log.error(f"扣减库存异常 [gift_id={gift_id}, retry={retry_count}]: {e}")

        log.warning(f"扣减库存超过最大重试次数 [gift_id={gift_id}, retries={max_retries}]")
        return False, False

    def do_exchange(self, user_id: int, gift_id: int) -> Dict[str, Any]:
        """
        执行兑换：校验礼物可兑换且库存、用户积分足够，扣库存、扣积分并记录历史。
        """
        # 1. 查询礼物：需可兑换、有库存
        gift = _row('t_gift', gift_id)
        if not gift:
            return _err("礼物不存在")
        stock = gift.get('stock')
        if gift.get('exchange') != 1:
            return _err("该奖品不可兑换")
        if not isinstance(stock, (int, float)) or int(stock) <= 0:
            return _err("库存不足")

        cost = max(0, _as_int(gift.get('cost')))

        # 2. 查询用户积分
        user = _row('t_user', user_id, "id,score,inventory")
        if not user or (user.get('score') or 0) < cost:
            return _err("用户不存在" if not user else "积分不足")

        # 3. 扣库存
        db_mgr.set_data('t_gift', {'id': gift_id, 'stock': int(stock) - 1})

        # 4. 扣积分并记录历史
        exchange_msg = f"兑换[{gift.get('id')}]{gift.get('name', '')}"
        add_ret = db_mgr.add_score(user_id, -cost, 'exchange', exchange_msg, out_key=str(gift_id))
        if add_ret.get('code') != 0:
            return add_ret

        self._write_gift_history(user_id, [gift], pool_id=-1, msg=exchange_msg)

        inv = json.loads(user.get('inventory') or '{}')
        if gift.get('cate_id') is not None:
            k = str(int(gift['cate_id']))
            inv[k] = inv.get(k, 0) + 1
        if db_mgr.set_data('t_user', {'id': user_id, 'inventory': json.dumps(inv)}).get('code') != 0:
            return _err("更新背包失败")

        log.info(f"Exchange: user_id={user_id}, gift_id={gift_id}, cost={cost}")
        return {"code": 0, "msg": "兑换成功", "data": {"gift": gift, "cost": cost}}

    def undo_lottery(self, history_id: int) -> Dict[str, Any]:
        """
        撤销一次抽奖/兑换：删除该条积分历史、将用户积分恢复为操作前、对应礼物库存 +1。
        仅支持 action 为 lottery 或 exchange 且 out_key 有值的记录。
        """
        rec = _row('t_score_history', history_id)
        if not rec:
            return _err("历史记录不存在")

        action = (rec.get('action') or '').strip()
        out_key = rec.get('out_key')
        user_id, pre_value = rec.get('user_id'), rec.get('pre_value')
        if action not in ('lottery', 'exchange'):
            return _err("仅支持撤销抽奖/兑换记录")
        if not out_key or (isinstance(out_key, str) and not str(out_key).strip()):
            return _err("该记录无关联奖品，无法撤销")
        if user_id is None or pre_value is None:
            return _err("历史数据不完整")
        uid, score_before = int(user_id), int(pre_value)

        gift_id_counts = Counter(
            int(part.strip())
            for part in str(out_key).split(',')
            if part.strip().lstrip('-').isdigit()
        )
        if not gift_id_counts:
            return _err("该记录无关联奖品，无法撤销")

        # 查找未核销的礼物记录，并扣减背包
        gh_res = db_mgr.get_list(
            't_gift_history', 1, 500, '*',
            {'user_id': uid, 'gift_id': {'in': list(gift_id_counts.keys())}, 'status': 1},
        )
        gh_rows = (gh_res.get('data') or {}).get('data') or [] if gh_res.get('code') == 0 else []
        by_gift: Dict[int, List[Dict[str, Any]]] = {}
        for row in gh_rows:
            gid = row.get('gift_id')
            if gid is not None:
                by_gift.setdefault(int(gid), []).append(row)

        to_delete: List[int] = []
        cate_counts: Counter = Counter()
        for gid, need in gift_id_counts.items():
            rows = sorted(by_gift.get(gid, []), key=lambda r: r.get('id') or 0, reverse=True)
            if len(rows) < need:
                return _err("礼物记录不足或已核销，无法撤销")
            for row in rows[:need]:
                to_delete.append(int(row['id']))
                cate_id = row.get('gift_cate_id')
                if cate_id is None:
                    g = _row('t_gift', gid, 'cate_id')
                    cate_id = g.get('cate_id') if g else None
                if cate_id is not None:
                    cate_counts[str(int(cate_id))] += 1

        inv_user = _row('t_user', uid, 'id,inventory,score')
        if not inv_user:
            return _err("用户不存在")
        inv = json.loads(inv_user.get('inventory') or '{}')
        for key, need in cate_counts.items():
            if inv.get(key, 0) < need:
                return _err("背包库存不足，无法撤销")
            inv[key] -= need
            if inv[key] <= 0:
                del inv[key]
        if db_mgr.set_data('t_user', {
            'id': uid,
            'inventory': json.dumps(inv),
            'score': score_before,
        }).get('code') != 0:
            return _err("恢复用户数据失败")

        for gh_id in to_delete:
            db_mgr.del_data('t_gift_history', gh_id)

        # 礼物库存 +1（支持 out_key 为逗号分隔的多个礼物 id，包含重复 ID）
        for gid, count in gift_id_counts.items():
            g = _row('t_gift', gid, 'id,stock')
            if g and isinstance(g.get('stock'), (int, float)):
                db_mgr.set_data('t_gift', {'id': gid, 'stock': int(g['stock']) + count})

        # 删除积分历史
        if db_mgr.del_data('t_score_history', history_id).get('code') != 0:
            return _err("删除历史记录失败")

        log.info(f"Undo {action}: history_id={history_id}, user_id={uid}")
        return {"code": 0, "msg": "撤销成功", "data": {"user_id": uid, "score": score_before}}

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

        resp = db_mgr.get_list('t_gift', 1, 1000, ['cost', 'cate_id', 'stock'], conditions or None)
        gifts = (resp.get('data') or {}).get('data') or [] if resp.get('code') == 0 else []
        if not gifts:
            return _err("Failed to query gift list")

        weighted_sum = 0.0
        total_stock = 0
        by_cate: Dict[Any, tuple] = {}
        for g in gifts:
            c, s = g.get('cost'), g.get('stock')
            if not isinstance(c, (int, float)) or not isinstance(s, (int, float)):
                continue
            cost_val, stock_val = float(c), int(s)
            if stock_val < 0:
                continue
            weighted_sum += cost_val * stock_val
            total_stock += stock_val
            cate_id = g.get('cate_id')
            prev_w, prev_s = by_cate.get(cate_id, (0.0, 0))
            by_cate[cate_id] = (prev_w + cost_val * stock_val, prev_s + stock_val)

        cate_name_map: Dict[Any, str] = {}
        cate_resp = db_mgr.get_list('t_gift_category', 1, 1000, ['id', 'name'], None)
        if cate_resp.get('code') == 0:
            for c_row in (cate_resp.get('data') or {}).get('data') or []:
                if c_row.get('id') is not None:
                    cate_name_map[c_row['id']] = c_row.get('name') or ''

        if total_stock <= 0:
            return _err("No matching gifts or zero total stock")

        by_category = []
        for cate_id, (cate_weighted, cate_stock) in sorted(
            by_cate.items(),
            key=lambda item: (item[0] is None, item[0] if item[0] is not None else 0),
        ):
            by_category.append({
                "cate_id": cate_id,
                "cate_name": cate_name_map.get(cate_id),
                "avg_cost": cate_weighted / cate_stock if cate_stock > 0 else 0.0,
                "count": cate_stock,
            })

        return {
            "code": 0,
            "msg": "ok",
            "data": {
                "avg_cost": weighted_sum / total_stock,
                "total_count": total_stock,
                "by_category": by_category,
            },
        }

    def redeem(self, history_id: int) -> Dict[str, Any]:
        """
        核销/取消核销礼物记录：切换 t_gift_history.status（1↔2），并同步扣减/恢复用户背包。
        背包格式：t_user.inventory = {"3":1,"4":1}，键为 gift_cate_id。
        """
        rec = _row('t_gift_history', history_id)
        if not rec:
            return _err("礼物记录不存在")

        cur_status = _as_int(rec.get('status'), 1) or 1
        new_status = 2 if cur_status == 1 else 1
        user_id, cate_id = rec.get('user_id'), rec.get('gift_cate_id')
        if user_id is None or cate_id is None:
            return _err("记录缺少用户信息" if user_id is None else "记录缺少分类信息，无法核销")
        uid, cid = int(user_id), int(cate_id)

        user_data = _row('t_user', uid, 'id,inventory')
        if not user_data:
            return _err("用户不存在")

        original_inventory = user_data.get('inventory') or '{}'
        inv = json.loads(original_inventory)
        cate_key = str(cid)
        if new_status == 2:
            if inv.get(cate_key, 0) < 1:
                return _err("背包库存不足，无法核销")
            inv[cate_key] -= 1
            if inv[cate_key] <= 0:
                del inv[cate_key]
        else:
            inv[cate_key] = inv.get(cate_key, 0) + 1

        inventory_str = json.dumps(inv)
        if db_mgr.set_data('t_user', {'id': uid, 'inventory': inventory_str}).get('code') != 0:
            return _err("更新背包失败")

        if db_mgr.set_data('t_gift_history', {'id': history_id, 'status': new_status}).get('code') != 0:
            # 回滚背包
            db_mgr.set_data('t_user', {'id': uid, 'inventory': original_inventory})
            return _err("更新核销状态失败")

        msg = "核销成功" if new_status == 2 else "已取消核销"
        log.info(
            f"Redeem: history_id={history_id}, user_id={uid}, cate_id={cid}, "
            f"status {cur_status}->{new_status}, inventory={inventory_str}"
        )
        return {
            "code": 0,
            "msg": msg,
            "data": {
                "history_id": history_id,
                "user_id": uid,
                "status": new_status,
                "inventory": inventory_str,
            },
        }


lottery_mgr = LotteryMgr()
