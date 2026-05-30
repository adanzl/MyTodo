from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any, Dict


_EMPTY_REST_DAYS: Dict[str, Any] = {"weekdays": [], "dates": [], "work_dates": []}


def parse_rest_days(rest_days_raw: Any) -> Dict[str, Any]:
    """
    rest_days 存库为 JSON string（或在写路径/内存中为 dict）。
    这里做一次 parse，让后续计算都基于 dict，避免循环里反复 json.loads。
    """
    if not rest_days_raw:
        return dict(_EMPTY_REST_DAYS)
    rule = json.loads(rest_days_raw) if isinstance(rest_days_raw, str) else rest_days_raw
    if isinstance(rule, str):
        rule = json.loads(rule)
    if not isinstance(rule, dict):
        return dict(_EMPTY_REST_DAYS)
    return {
        "weekdays": list(rule.get("weekdays") or []),
        "dates": list(rule.get("dates") or []),
        "work_dates": list(rule.get("work_dates") or []),
    }


def is_rest_day(rule: Dict[str, Any], d: date) -> bool:
    if not rule:
        return False

    day_key = d.strftime("%Y-%m-%d")
    if day_key in (rule.get("work_dates") or []):
        return False
    if day_key in (rule.get("dates") or []):
        return True
    weekdays = rule.get("weekdays") or []
    if not weekdays:
        return False
    # python weekday(): Mon=0..Sun=6 -> rule weekday: Sun=0..Sat=6
    wd = (d.weekday() + 1) % 7
    return wd in weekdays


def get_workday_index(start_date: date, target_date: date, rule: Dict[str, Any]) -> int:
    """
    返回 target_date 对应的工作日序号（0-based）。
    - target < start: -1
    - target 是休息日且在范围内：返回 -2（用于区分“休息日当天”）
    """
    if target_date < start_date:
        return -1
    if is_rest_day(rule, target_date):
        return -2
    idx = -1
    cur = start_date
    while cur <= target_date:
        if not is_rest_day(rule, cur):
            idx += 1
        cur = cur + timedelta(days=1)
    return idx


def end_date_by_work_duration(start_date: date, duration: int, rule: Dict[str, Any]) -> date:
    """duration=工作日天数，计算最后一个工作日对应的自然日。"""
    if duration <= 0:
        return start_date
    need = duration - 1  # 0-based
    seen = -1
    cur = start_date
    while True:
        if not is_rest_day(rule, cur):
            seen += 1
            if seen == need:
                return cur
        cur = cur + timedelta(days=1)

