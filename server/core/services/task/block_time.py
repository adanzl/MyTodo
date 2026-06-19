"""任务禁用时段（block_time）解析与判断。

支持任务级与全局级配置，数据结构一致：
- blacklist：当前时间在时段内则禁用
- whitelist：当前时间不在允许时段内则禁用

全局配置存 Redis，key 与 setRdsData/getRdsData 约定一致：
  table=task:block_time, id=global -> task:block_time:global
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Dict, Optional

from core.config import app_logger
from core.db import rds_mgr

log = app_logger

GLOBAL_BLOCK_TIME_RDS_TABLE = "task:block_time"
GLOBAL_BLOCK_TIME_RDS_ID = "global"
_GLOBAL_CACHE_TTL_SEC = 30
_COMMON_ROLES = (None, "", "common")

_UNCACHED = object()
_global_cache_config: Any = _UNCACHED
_global_cache_at: float = 0.0


def global_block_time_redis_key() -> str:
    return f"{GLOBAL_BLOCK_TIME_RDS_TABLE}:{GLOBAL_BLOCK_TIME_RDS_ID}"


def invalidate_global_block_time_cache() -> None:
    """清除全局配置进程内缓存（测试或写入后可选调用）。"""
    global _global_cache_config, _global_cache_at
    _global_cache_config, _global_cache_at = _UNCACHED, 0.0


def get_global_block_time_config(*, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """从 Redis 读取全局 block_time，解析后缓存（30s TTL）。"""
    global _global_cache_config, _global_cache_at
    now_mono = time.monotonic()
    if not force_refresh and _global_cache_config is not _UNCACHED and now_mono - _global_cache_at < _GLOBAL_CACHE_TTL_SEC:
        return _global_cache_config
    try:
        raw = rds_mgr.get_str(global_block_time_redis_key())
    except Exception as e:
        log.warning(f"读取全局 block_time 失败: {e}")
        raw = ""
    _global_cache_config = parse_block_time_config(raw)
    _global_cache_at = now_mono
    return _global_cache_config


def parse_block_time_config(block_time_raw: str) -> Optional[Dict[str, Any]]:
    """解析 block_time JSON 字符串；无效或空配置返回 None。"""
    if not block_time_raw or block_time_raw == "{}":
        return None
    try:
        return json.loads(block_time_raw)
    except json.JSONDecodeError:
        return None


def _is_blocked_by_config(data: Optional[Dict[str, Any]], now: datetime) -> bool:
    if not data:
        return False
    block_type = data.get("type") or "blacklist"
    rules = data.get("whitelist" if block_type == "whitelist" else "blacklist") or []
    common = next((r for r in rules if r.get("role") in _COMMON_ROLES), None)
    if not common:
        return False
    slots = common.get("time") or []
    if block_type == "whitelist" and not slots:
        return False

    # python weekday(): Mon=0..Sun=6 -> rule weekday: Sun=0..Sat=6
    wd, t = (now.weekday() + 1) % 7, now.time()
    in_slot = False
    for slot in slots:
        weekdays = slot.get("weekdays") or []
        if weekdays and wd not in weekdays:
            continue
        start_s, end_s = slot.get("start"), slot.get("end")
        if not start_s or not end_s:
            continue
        start = end = None
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                start = datetime.strptime(start_s, fmt).time()
                end = datetime.strptime(end_s, fmt).time()
                break
            except ValueError:
                continue
        if start is None or end is None:
            continue
        # 判断时刻是否落在 [start, end) 内，支持跨午夜（如 22:00-07:00）
        if (start <= t < end) if start <= end else (t >= start or t < end):
            in_slot = True
            break
    return not in_slot if block_type == "whitelist" else in_slot


def is_global_block_time_now(date_str: str, *, now: Optional[datetime] = None) -> bool:
    """当前时刻是否处于全局禁用时段。"""
    now = now or datetime.now()
    if date_str != now.strftime("%Y-%m-%d"):
        return False
    return _is_blocked_by_config(get_global_block_time_config(), now)


def is_in_block_time_now(
    block_time_raw: str,
    date_str: str,
    *,
    now: Optional[datetime] = None,
) -> bool:
    """判断指定日期当前时刻是否应因 block_time 配置而锁定。

    Args:
        block_time_raw: block_time JSON 字符串
        date_str: 查询日期（YYYY-MM-DD），仅当为今天时才生效
        now: 可选，用于测试注入当前时刻

    Returns:
        是否应锁定
    """
    now = now or datetime.now()
    if date_str != now.strftime("%Y-%m-%d"):
        return False
    return _is_blocked_by_config(parse_block_time_config(block_time_raw), now)
