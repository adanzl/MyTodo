from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from core.config import app_logger
from core.db.db_mgr import db_mgr

log = app_logger


class UserStats(TypedDict):
    lotteryCount: int  # 抽奖次数
    lotteryCost: int  # 抽奖花费
    exchangeCount: int  # 兑换次数
    exchangeCost: int  # 兑换花费
    taskCount: int  # 完成任务数
    taskIncome: int  # 任务收益
    adminCount: int  # 后台操作次数
    adminIncome: int  # 后台操作汇总(保留正负号)


class CategoryStat(TypedDict):
    cate_id: Optional[int]  # 分类ID
    cate_name: str  # 分类名称
    win_count: int  # 中奖次数
    gift_types: int  # 礼物种类数
    total_cost: float  # 总花费
    total_exchange_price: int  # 实际中奖礼物兑换价格总和
    won_gifts: List[Dict[str, Any]]  # 中奖物品列表[{id, name, count, img, cost}]


class LotteryStatsResult(TypedDict):
    stats: UserStats  # 用户基础统计数据
    categoryStats: List[CategoryStat]  # 各分类中奖统计列表(按中奖次数降序)


class StatsMgr:

    def __init__(self):
        self._db = db_mgr

    def get_user_lottery_stats(self,
                               user_id: int = 3,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> LotteryStatsResult:
        """获取用户统计数据"""
        try:
            # 构建查询条件
            conditions: Dict[str, Any] = {'user_id': user_id}
            if start_date and end_date:
                conditions['dt'] = {">=": start_date, "<=": end_date + " 23:59:59"}

            # 循环获取积分历史
            all_records = []
            page, page_size = 1, 100
            while True:
                res = self._db.get_list('t_score_history', page, page_size, '*', conditions)
                if res.get('code') != 0:
                    break

                records = (res.get('data') or {}).get('data') or []
                if not records:
                    break

                all_records.extend(records)
                if len(records) < page_size:
                    break
                page += 1

            if not all_records:
                return self._empty_result()

            # 统计数据
            lottery_count = lottery_cost = exchange_count = exchange_cost = task_count = task_income = admin_count = admin_income = 0
            category_map: Dict[int, Dict[str, Any]] = {}

            for record in all_records:
                # 跳过非字典类型
                if not isinstance(record, dict):
                    log.warning(f"跳过无效记录: {type(record)}")
                    continue

                action, value, out_key = record.get('action'), record.get('value', 0), record.get('out_key')

                if action == 'lottery':
                    lottery_count += 1
                    lottery_cost += abs(value)
                    if out_key:
                        self._process_gift_record(action, value, out_key, category_map)
                elif action == 'exchange':
                    exchange_count += 1
                    exchange_cost += abs(value)
                    if out_key:
                        self._process_gift_record(action, value, out_key, category_map)
                elif action == 'schedule' and value > 0:
                    task_count += 1
                    task_income += value
                elif action == 'appAdmin':
                    admin_count += 1
                    admin_income += value

            # 构建分类统计
            category_stats = self._build_category_stats(category_map)
            category_stats.sort(key=lambda x: x['win_count'], reverse=True)

            return {
                'stats': {
                    'lotteryCount': lottery_count,
                    'lotteryCost': lottery_cost,
                    'exchangeCount': exchange_count,
                    'exchangeCost': exchange_cost,
                    'taskCount': task_count,
                    'taskIncome': task_income,
                    'adminCount': admin_count,
                    'adminIncome': admin_income,
                },
                'categoryStats': category_stats
            }
        except Exception as e:
            log.error(f"统计失败: {e}")
            return self._empty_result()

    def _empty_result(self) -> LotteryStatsResult:
        """返回空统计结果"""
        return {
            'stats': {
                'lotteryCount': 0,
                'lotteryCost': 0,
                'exchangeCount': 0,
                'exchangeCost': 0,
                'taskCount': 0,
                'taskIncome': 0,
                'adminCount': 0,
                'adminIncome': 0,
            },
            'categoryStats': []
        }

    def _process_gift_record(self, action: str, value: int, out_key: str, category_map: Dict):
        """处理礼物记录（抽奖或兑换）"""
        if action == 'lottery':
            gift_ids = [int(id.strip()) for id in out_key.split(',') if id.strip().isdigit()]
            res = self._db.get_list('t_gift', 1, len(gift_ids), '*', {'id': {'in': gift_ids}})
            gifts = (res.get('data') or {}).get('data') or []
            gift_map = {g['id']: g for g in gifts}

            for gift_id in gift_ids:
                gift = gift_map.get(gift_id)
                if gift:
                    self._update_category(gift.get('cate_id'), gift_id, abs(value / len(gift_ids)), category_map, gift)
        else:  # exchange
            gift_id = int(out_key)
            res = self._db.get_list('t_gift', 1, 1, '*', {'id': gift_id})
            gift_data = ((res.get('data') or {}).get('data') or [{}])[0]
            if gift_data:
                self._update_category(gift_data.get('cate_id'), gift_id, abs(value), category_map, gift_data)

    def _update_category(self, cate_id: Optional[int], gift_id: int, cost: float, category_map: Dict, gift_info: Optional[Dict] = None):
        """更新分类统计"""
        if cate_id is None:
            return
        if cate_id not in category_map:
            category_map[cate_id] = {
                'cate_id': cate_id,
                'cate_name': self._get_category_name(cate_id),
                'win_count': 0,
                'gift_ids': set(),
                'total_cost': 0,
                'won_gifts_map': {},  # {gift_id: {id, name, count, img}}
            }
        category_map[cate_id]['win_count'] += 1
        category_map[cate_id]['gift_ids'].add(gift_id)
        category_map[cate_id]['total_cost'] += cost
        
        # 收集中奖物品信息
        if gift_info and gift_id not in category_map[cate_id]['won_gifts_map']:
            category_map[cate_id]['won_gifts_map'][gift_id] = {
                'id': gift_id,
                'name': gift_info.get('name', ''),
                'count': 0,
                'img': gift_info.get('img', ''),
                'cost': gift_info.get('cost', 0),
            }
        if gift_id in category_map[cate_id]['won_gifts_map']:
            category_map[cate_id]['won_gifts_map'][gift_id]['count'] += 1

    def _build_category_stats(self, category_map: Dict) -> List[CategoryStat]:
        """构建分类统计列表"""
        category_stats = []
        for cate_id, stat in category_map.items():
            gift_ids = list(stat['gift_ids'])
            total_exchange_price = 0
            if gift_ids:
                res = self._db.get_list('t_gift', 1, len(gift_ids), 'cost', {'id': {'in': gift_ids}})
                gifts = (res.get('data') or {}).get('data') or []
                total_exchange_price = sum(g.get('cost', 0) for g in gifts)

            # 将 won_gifts_map 转换为列表，按次数降序
            won_gifts = sorted(
                stat.get('won_gifts_map', {}).values(),
                key=lambda x: x['count'],
                reverse=True
            )

            category_stats.append({
                'cate_id': cate_id,
                'cate_name': stat['cate_name'],
                'win_count': stat['win_count'],
                'gift_types': len(stat['gift_ids']),
                'total_cost': round(stat['total_cost'], 2),
                'total_exchange_price': total_exchange_price,
                'won_gifts': won_gifts,
            })
        return category_stats

    def _get_category_name(self, cate_id: int) -> str:
        """获取分类名称"""
        if not cate_id:
            return '未分类'
        res = self._db.get_data('t_gift_category', cate_id, 'name')
        data = res.get('data') or {}
        return data.get('name', f'分类{cate_id}')


stats_mgr = StatsMgr()
