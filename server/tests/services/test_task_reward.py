import importlib
import json
from unittest.mock import MagicMock

from core.services.task.reward import (
    TASK_REWARD_ACTION,
    TASK_REWARD_RDS_ID,
    TASK_REWARD_RDS_TABLE,
    get_reward_config,
    is_reward_active,
    parse_reward_config,
    reward_redis_key,
)

task_mgr_module = importlib.import_module("core.services.task.task_mgr")
TaskMgr = task_mgr_module.TaskMgr


def test_reward_redis_key():
    assert reward_redis_key() == f"{TASK_REWARD_RDS_TABLE}:{TASK_REWARD_RDS_ID}"
    assert reward_redis_key() == "task:reward"


def test_parse_reward_config_ok():
    raw = json.dumps({"reward": 10, "start_date": "2026-08-01", "end_date": "2026-08-31"})
    cfg = parse_reward_config(raw)
    assert cfg == {"reward": 10, "start_date": "2026-08-01", "end_date": "2026-08-31"}


def test_parse_reward_config_invalid():
    assert parse_reward_config("") is None
    assert parse_reward_config("{") is None
    assert parse_reward_config({"reward": 10}) is None
    assert parse_reward_config({"reward": 10, "start_date": "2026-08-31", "end_date": "2026-08-01"}) is None
    assert parse_reward_config({"reward": "x", "start_date": "2026-08-01", "end_date": "2026-08-31"}) == {
        "reward": 0,
        "start_date": "2026-08-01",
        "end_date": "2026-08-31",
    }


def test_is_reward_active():
    cfg = {"reward": 5, "start_date": "2026-08-01", "end_date": "2026-08-03"}
    assert is_reward_active(cfg, "2026-08-01") is True
    assert is_reward_active(cfg, "2026-08-03") is True
    assert is_reward_active(cfg, "2026-07-31") is False
    assert is_reward_active({"reward": 0, "start_date": "2026-08-01", "end_date": "2026-08-03"}, "2026-08-01") is False
    assert is_reward_active(None, "2026-08-01") is False


def test_get_reward_config(monkeypatch):
    monkeypatch.setattr(
        "core.services.task.reward.rds_mgr.get_str",
        lambda key: json.dumps({"reward": 8, "start_date": "2026-08-01", "end_date": "2026-08-10"})
        if key == "task:reward" else "",
    )
    assert get_reward_config()["reward"] == 8


def _daily_task(task_id: int, completed: bool, user_id: int = 3) -> dict:
    return {
        "id": task_id,
        "name": f"task-{task_id}",
        "type": 0,
        "start_date": "2026-08-01",
        "end_date": "2026-08-31",
        "duration": 10,
        "user_id": str(user_id),
        "data": json.dumps({
            "dailyMaterials": {
                "0": [{"id": task_id * 10, "status": {str(user_id): 1 if completed else 0}}],
            }
        }),
    }


def test_try_grant_daily_reward_success(monkeypatch):
    cfg = {"reward": 7, "start_date": "2026-08-01", "end_date": "2026-08-31"}
    monkeypatch.setattr(task_mgr_module, "get_reward_config", lambda: cfg)
    monkeypatch.setattr(task_mgr_module, "is_reward_active", lambda c, d: True)

    calls = []

    def fake_get_list(table, page_num=1, page_size=20, fields='*', conditions=None):
        if table == "t_score_history":
            return {"code": 0, "data": {"data": []}}
        return {"code": 0, "data": {"data": [_daily_task(1, True), _daily_task(2, True)]}}

    def fake_add_score(**kwargs):
        calls.append(kwargs)
        return {"code": 0, "data": 100}

    monkeypatch.setattr(task_mgr_module.db_mgr, "get_list", fake_get_list)
    monkeypatch.setattr(task_mgr_module.db_mgr, "add_score", fake_add_score)

    bonus = TaskMgr()._try_grant_daily_reward(3, "2026-08-01")
    assert bonus == 7
    assert calls[0]["action"] == TASK_REWARD_ACTION
    assert calls[0]["value"] == 7
    assert calls[0]["out_key"] == "2026-08-01"


def test_try_grant_daily_reward_skips_incomplete(monkeypatch):
    cfg = {"reward": 7, "start_date": "2026-08-01", "end_date": "2026-08-31"}
    monkeypatch.setattr(task_mgr_module, "get_reward_config", lambda: cfg)
    monkeypatch.setattr(task_mgr_module, "is_reward_active", lambda c, d: True)

    def fake_get_list(table, page_num=1, page_size=20, fields='*', conditions=None):
        if table == "t_score_history":
            return {"code": 0, "data": {"data": []}}
        return {"code": 0, "data": {"data": [_daily_task(1, True), _daily_task(2, False)]}}

    add_score = MagicMock()
    monkeypatch.setattr(task_mgr_module.db_mgr, "get_list", fake_get_list)
    monkeypatch.setattr(task_mgr_module.db_mgr, "add_score", add_score)

    assert TaskMgr()._try_grant_daily_reward(3, "2026-08-01") == 0
    add_score.assert_not_called()


def test_try_grant_daily_reward_already_granted(monkeypatch):
    cfg = {"reward": 7, "start_date": "2026-08-01", "end_date": "2026-08-31"}
    monkeypatch.setattr(task_mgr_module, "get_reward_config", lambda: cfg)
    monkeypatch.setattr(task_mgr_module, "is_reward_active", lambda c, d: True)

    def fake_get_list(table, page_num=1, page_size=20, fields='*', conditions=None):
        if table == "t_score_history":
            return {"code": 0, "data": {"data": [{"id": 1}]}}
        raise AssertionError("should not query tasks after already granted")

    monkeypatch.setattr(task_mgr_module.db_mgr, "get_list", fake_get_list)
    assert TaskMgr()._try_grant_daily_reward(3, "2026-08-01") == 0


def test_try_grant_ignores_continuous_tasks(monkeypatch):
    cfg = {"reward": 7, "start_date": "2026-08-01", "end_date": "2026-08-31"}
    monkeypatch.setattr(task_mgr_module, "get_reward_config", lambda: cfg)
    monkeypatch.setattr(task_mgr_module, "is_reward_active", lambda c, d: True)

    continuous = _daily_task(9, False)
    continuous["type"] = 1
    daily = _daily_task(1, True)

    def fake_get_list(table, page_num=1, page_size=20, fields='*', conditions=None):
        if table == "t_score_history":
            return {"code": 0, "data": {"data": []}}
        return {"code": 0, "data": {"data": [continuous, daily]}}

    calls = []
    monkeypatch.setattr(task_mgr_module.db_mgr, "get_list", fake_get_list)
    monkeypatch.setattr(
        task_mgr_module.db_mgr,
        "add_score",
        lambda **kwargs: calls.append(kwargs) or {"code": 0},
    )
    assert TaskMgr()._try_grant_daily_reward(3, "2026-08-01") == 7
    assert len(calls) == 1


def test_finish_material_grants_bonus(monkeypatch):
    task = _daily_task(1, False)
    task_data = json.loads(task["data"])
    task["data"] = json.dumps(task_data)

    def fake_get_data(table, row_id, fields):
        return {"code": 0, "data": dict(task)}

    monkeypatch.setattr(task_mgr_module.db_mgr, "get_data", fake_get_data)
    monkeypatch.setattr(task_mgr_module.db_mgr, "set_data", lambda *a, **k: {"code": 0})
    monkeypatch.setattr(task_mgr_module.db_mgr, "add_score", lambda **k: {"code": 0})
    monkeypatch.setattr(TaskMgr, "_try_grant_daily_reward", lambda self, uid, d: 10)

    result = TaskMgr().finish_material(1, 10, "2026-08-01", 3)
    assert result["code"] == 0
    assert result["data"]["bonus"] == 10
    assert result["data"]["score"] == 0
