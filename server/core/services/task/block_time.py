"""任务禁用时段（block_time）解析与判断。

数据结构（按 user_id 分人，无 common）：
{
  "3": { "type": "blacklist"|"whitelist", "blacklist": [slots], "whitelist": [slots] },
  "4": { ... }
}
某 user_id 无配置 = 该层不限制。

全局配置存 Redis：task:block_time:global
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


def parse_block_time_config(block_time_raw: Any) -> Optional[Dict[str, Any]]:
    """解析 block_time JSON；无效或空配置返回 None。"""
    if not block_time_raw or block_time_raw == "{}":
        return None
    if isinstance(block_time_raw, dict):
        return block_time_raw or None
    if not isinstance(block_time_raw, str):
        return None
    try:
        data = json.loads(block_time_raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not data:
        return None
    return data


def _get_user_entry(config: Optional[Dict[str, Any]], user_id: int) -> Optional[Dict[str, Any]]:
    if not config or user_id <= 0:
        return None
    entry = config.get(str(user_id))
    return entry if isinstance(entry, dict) else None


def _slot_matches(slot: Dict[str, Any], wd: int, t) -> bool:
    weekdays = slot.get("weekdays") or []
    if weekdays and wd not in weekdays:
        return False
    start_s, end_s = slot.get("start"), slot.get("end")
    if not start_s or not end_s:
        return False
    start = end = None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            start = datetime.strptime(start_s, fmt).time()
            end = datetime.strptime(end_s, fmt).time()
            break
        except ValueError:
            continue
    if start is None or end is None:
        return False
    return (start <= t < end) if start <= end else (t >= start or t < end)


def _is_blocked_by_entry(entry: Dict[str, Any], now: datetime) -> bool:
    block_type = entry.get("type") or "blacklist"
    slots = entry.get("whitelist" if block_type == "whitelist" else "blacklist") or []
    if block_type == "whitelist" and not slots:
        return False

    wd, t = (now.weekday() + 1) % 7, now.time()
    in_slot = any(_slot_matches(slot, wd, t) for slot in slots if isinstance(slot, dict))
    return not in_slot if block_type == "whitelist" else in_slot


def is_global_block_time_now(
    date_str: str,
    user_id: int,
    *,
    now: Optional[datetime] = None,
) -> bool:
    """当前时刻是否处于该用户的全局禁用时段。"""
    now = now or datetime.now()
    if date_str != now.strftime("%Y-%m-%d"):
        return False
    entry = _get_user_entry(get_global_block_time_config(), user_id)
    if not entry:
        return False
    return _is_blocked_by_entry(entry, now)


def is_in_block_time_now(
    block_time_raw: Any,
    date_str: str,
    user_id: int,
    *,
    now: Optional[datetime] = None,
) -> bool:
    """判断指定日期当前时刻是否应因任务级 block_time 而锁定。"""
    now = now or datetime.now()
    if date_str != now.strftime("%Y-%m-%d"):
        return False
    entry = _get_user_entry(parse_block_time_config(block_time_raw), user_id)
    if not entry:
        return False
    return _is_blocked_by_entry(entry, now)
