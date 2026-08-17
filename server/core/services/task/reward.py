"""每日全勤奖励配置。

当天所有非持续（每日）任务完成后，按 Redis 配置发放额外星星。
配置存 Redis key：task:reward，JSON 示例：
{
  "reward": 10,
  "start_date": "2026-08-01",
  "end_date": "2026-08-31"
}
日期单位为天（YYYY-MM-DD），闭区间。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional

from core.config import app_logger
from core.db import rds_mgr

log = app_logger

TASK_REWARD_RDS_TABLE = "task"
TASK_REWARD_RDS_ID = "reward"
TASK_REWARD_ACTION = "task_reward"


def reward_redis_key() -> str:
    return f"{TASK_REWARD_RDS_TABLE}:{TASK_REWARD_RDS_ID}"


def _parse_day(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None
    return text


def parse_reward_config(raw: Any) -> Optional[Dict[str, Any]]:
    """解析 task:reward JSON；无效或星星<=0 时仍返回结构，由调用方判断是否发放。"""
    data: Any = raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict):
        return None

    try:
        reward = int(data.get("reward") or 0)
    except (TypeError, ValueError):
        reward = 0
    start_date = _parse_day(data.get("start_date"))
    end_date = _parse_day(data.get("end_date"))
    if not start_date or not end_date:
        return None
    if start_date > end_date:
        return None
    return {
        "reward": max(0, reward),
        "start_date": start_date,
        "end_date": end_date,
    }


def get_reward_config() -> Optional[Dict[str, Any]]:
    """从 Redis 读取全勤奖励配置。"""
    try:
        raw = rds_mgr.get_str(reward_redis_key())
    except Exception as e:
        log.warning(f"读取任务奖励配置失败: {e}")
        return None
    return parse_reward_config(raw)


def is_reward_active(config: Optional[Dict[str, Any]], date_str: str) -> bool:
    """指定日期是否处于奖励活动期内，且星星数量大于 0。"""
    if not config:
        return False
    reward = int(config.get("reward") or 0)
    if reward <= 0:
        return False
    start_date = config.get("start_date") or ""
    end_date = config.get("end_date") or ""
    return bool(start_date <= date_str <= end_date)
