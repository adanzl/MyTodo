import importlib
import json
from datetime import datetime

task_mgr_module = importlib.import_module("core.services.task.task_mgr")
material_mgr_module = importlib.import_module("core.services.task.material_mgr")
from core.services.task.block_time import (
    GLOBAL_BLOCK_TIME_RDS_ID,
    GLOBAL_BLOCK_TIME_RDS_TABLE,
    get_global_block_time_config,
    global_block_time_redis_key,
    invalidate_global_block_time_cache,
    is_in_block_time_now,
    parse_block_time_config,
)

TaskMgr = task_mgr_module.TaskMgr
MaterialMgr = material_mgr_module.MaterialMgr

USER_CANCAN = 3


def _blacklist_raw(start: str, end: str, weekdays=None, user_id: int = USER_CANCAN) -> str:
    slot = {"start": start, "end": end}
    if weekdays is not None:
        slot["weekdays"] = weekdays
    return json.dumps(
        {
            str(user_id): {
                "type": "blacklist",
                "blacklist": [slot],
                "whitelist": [],
            }
        }
    )


def _whitelist_raw(start: str, end: str, user_id: int = USER_CANCAN) -> str:
    return json.dumps(
        {
            str(user_id): {
                "type": "whitelist",
                "blacklist": [],
                "whitelist": [{"start": start, "end": end}],
            }
        }
    )


TODAY = "2026-06-17"
NOW_IN_SLOT = datetime(2026, 6, 17, 10, 0, 0)
NOW_OUT_SLOT = datetime(2026, 6, 17, 14, 0, 0)


def test_global_block_time_redis_key():
    assert global_block_time_redis_key() == f"{GLOBAL_BLOCK_TIME_RDS_TABLE}:{GLOBAL_BLOCK_TIME_RDS_ID}"


def test_blacklist_in_slot():
    raw = _blacklist_raw("09:00:00", "12:00:00")
    assert is_in_block_time_now(raw, TODAY, USER_CANCAN, now=NOW_IN_SLOT) is True
    assert is_in_block_time_now(raw, TODAY, USER_CANCAN, now=NOW_OUT_SLOT) is False


def test_blacklist_no_config_for_user():
    raw = _blacklist_raw("09:00:00", "12:00:00", user_id=USER_CANCAN)
    assert is_in_block_time_now(raw, TODAY, 4, now=NOW_IN_SLOT) is False


def test_blacklist_not_today():
    raw = _blacklist_raw("09:00:00", "12:00:00")
    assert is_in_block_time_now(raw, "2026-06-16", USER_CANCAN, now=NOW_IN_SLOT) is False


def test_whitelist_outside_allowed():
    raw = _whitelist_raw("09:00:00", "12:00:00")
    assert is_in_block_time_now(raw, TODAY, USER_CANCAN, now=NOW_OUT_SLOT) is True
    assert is_in_block_time_now(raw, TODAY, USER_CANCAN, now=NOW_IN_SLOT) is False


def test_whitelist_empty_slots_not_locked():
    raw = json.dumps({"3": {"type": "whitelist", "blacklist": [], "whitelist": []}})
    assert is_in_block_time_now(raw, TODAY, USER_CANCAN, now=NOW_IN_SLOT) is False


def test_cross_midnight_blacklist():
    raw = _blacklist_raw("22:00:00", "07:00:00")
    assert is_in_block_time_now(raw, TODAY, USER_CANCAN, now=datetime(2026, 6, 17, 23, 0, 0)) is True
    assert is_in_block_time_now(raw, TODAY, USER_CANCAN, now=datetime(2026, 6, 17, 6, 30, 0)) is True
    assert is_in_block_time_now(raw, TODAY, USER_CANCAN, now=datetime(2026, 6, 17, 12, 0, 0)) is False


def test_weekday_filter():
    raw = _blacklist_raw("09:00:00", "12:00:00", weekdays=[0])
    assert is_in_block_time_now(raw, TODAY, USER_CANCAN, now=NOW_IN_SLOT) is False


def test_get_global_block_time_config_cached(monkeypatch):
    invalidate_global_block_time_cache()
    calls = {"n": 0}
    raw = '{"3":{"type":"blacklist","blacklist":[],"whitelist":[]}}'

    def fake_get_str(key):
        calls["n"] += 1
        assert key == global_block_time_redis_key()
        return raw

    monkeypatch.setattr("core.services.task.block_time.rds_mgr.get_str", fake_get_str)
    assert get_global_block_time_config() == parse_block_time_config(raw)
    assert get_global_block_time_config() == parse_block_time_config(raw)
    assert calls["n"] == 1


def _mock_material_status_db(monkeypatch, task_block_time: str):
    monkeypatch.setattr(MaterialMgr, "_get_active_unlimit", lambda *args, **kwargs: None)

    def fake_get_data(table, row_id, fields):
        if table == material_mgr_module.TABLE_MATERIAL:
            return {
                "code": 0,
                "data": {"type": 0, "duration": 0, "statistics": {}, "path": ""},
            }
        if table == material_mgr_module.TABLE_TASK:
            return {"code": 0, "data": {"block_time": task_block_time, "data": {}}}
        raise AssertionError(f"unexpected table: {table}")

    monkeypatch.setattr(material_mgr_module.db_mgr, "get_data", fake_get_data)


def test_material_status_falls_back_to_global_block_time(monkeypatch):
    invalidate_global_block_time_cache()
    _mock_material_status_db(monkeypatch, "{}")
    monkeypatch.setattr(
        material_mgr_module,
        "is_global_block_time_now",
        lambda *args, **_: True,
    )

    result = MaterialMgr().get_material_status(USER_CANCAN, material_id=1, task_id=10)
    assert result["data"]["lock"] == MaterialMgr.LOCK_CODE_GLOBAL_BLOCK
    assert result["data"]["reason"] == "当前处于全局禁用时段"


def test_material_status_task_block_time_overrides_global(monkeypatch):
    invalidate_global_block_time_cache()
    _mock_material_status_db(monkeypatch, _blacklist_raw("00:00:00", "23:59:59"))
    monkeypatch.setattr(
        material_mgr_module,
        "is_global_block_time_now",
        lambda *args, **_: False,
    )

    result = MaterialMgr().get_material_status(USER_CANCAN, material_id=1, task_id=10)
    assert result["data"]["lock"] == MaterialMgr.LOCK_CODE_TASK_BLOCK
    assert result["data"]["reason"] == "当前处于任务禁用时段"


def test_check_task_lock_pre_task_same_day_only(monkeypatch):
    """前置任务只检查 date_str 当天，不检查历史或其它天。"""
    calls = []

    def track_has_uncompleted(self, task, user_id, target_date):
        calls.append((task.get("name"), target_date.strftime("%Y-%m-%d")))
        return task.get("name") == "前置A"

    monkeypatch.setattr(TaskMgr, "_has_uncompleted_materials", track_has_uncompleted)

    tasks = [
        {"id": 10, "priority": 0, "name": "前置A", "block_time": "{}"},
        {"id": 2, "priority": 1, "name": "当前任务", "pre_task": "[10]", "block_time": "{}"},
    ]
    result = TaskMgr().check_task_lock(tasks, user_id=3, date_str=TODAY)
    locked = next(t for t in result if t["id"] == 2)
    assert locked["lock"] is True
    assert calls == [("前置A", TODAY)]


def test_check_task_lock_priority_minus_one_excluded(monkeypatch):
    """priority=-1 的任务不参与优先级锁定：不锁别人，也不被别人锁。"""
    def mock_has_uncompleted(self, task, user_id, target_date):
        return task.get("name") in ("高优先级未完成", "无优先级任务")

    monkeypatch.setattr(TaskMgr, "_has_uncompleted_materials", mock_has_uncompleted)

    tasks = [
        {"id": 1, "priority": 0, "name": "高优先级未完成", "block_time": "{}"},
        {"id": 2, "priority": 1, "name": "低优先级任务", "block_time": "{}"},
        {"id": 3, "priority": -1, "name": "无优先级任务", "block_time": "{}"},
    ]
    result = TaskMgr().check_task_lock(tasks, user_id=1, date_str=TODAY)
    by_id = {t["id"]: t for t in result}

    assert by_id[1]["lock"] is False
    assert by_id[2]["lock"] is True
    assert by_id[2]["msg"] == '请先完成 "高优先级未完成"'
    assert by_id[3]["lock"] is False
    assert by_id[3]["msg"] == ""
