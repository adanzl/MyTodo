"""播放列表加载失败或切换存储时，不得用内存快照覆盖持久化数据。"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import fakeredis
import pytest
from gevent import sleep

from core.db import rds_mgr
from core.services import playlist_mgr as pm
from core.services.playlist.constants import PLAYLIST_RDS_FULL_KEY, PLAYLIST_RDS_HISTORY_KEY


_START_SAVE_WORKER = pm.PlaylistRepository.start_save_worker


def collection(playlist_id="existing"):
    return {
        playlist_id: {
            "id": playlist_id,
            "name": playlist_id,
            "playlist": [],
            "pre_lists": [[] for _ in range(7)],
        }
    }


@pytest.fixture
def storage(monkeypatch):
    client = fakeredis.FakeRedis()
    monkeypatch.setenv("REDIS_ENABLED", "true")
    monkeypatch.setattr(rds_mgr, "rds", client)
    monkeypatch.setattr(rds_mgr, "_local_store", None)
    monkeypatch.setattr(rds_mgr, "is_local_fallback", False)
    monkeypatch.setattr(rds_mgr, "_client_generation", 0)
    monkeypatch.setattr(rds_mgr, "_create_redis_client", lambda: client)
    monkeypatch.setattr(pm, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(pm.PlaylistRepository, "start_save_worker", lambda self: None)
    monkeypatch.setattr(pm.PlaylistScheduling, "ensure_duration_guard_job", lambda self: None)
    monkeypatch.setattr(pm.PlaylistScheduling, "restore_timers_from_persistence", lambda self: None)
    monkeypatch.setattr(pm.PlaylistMgr, "_refresh_device_map", lambda self: None)
    monkeypatch.setattr(pm.PlaylistDevices, "refresh_single", lambda *args: None)
    monkeypatch.setattr(pm.PlaylistScheduling, "refresh_cron_job", lambda *args: None)
    return client


def fallback(monkeypatch, tmp_path):
    local = rds_mgr._LocalJsonStore(str(tmp_path / "fallback.json"))
    monkeypatch.setattr(rds_mgr, "_local_store", local)
    monkeypatch.setattr(rds_mgr, "is_local_fallback", True)
    return local


def test_queued_autosave_after_redis_recovers_cannot_erase_unloaded_data(
    storage, monkeypatch, tmp_path
):
    original = collection()
    storage.set(PLAYLIST_RDS_FULL_KEY, json.dumps(original))
    fallback(monkeypatch, tmp_path)
    mgr = pm.PlaylistMgr()

    assert mgr._playlist_raw == {}
    assert mgr._needs_reload is True
    assert rds_mgr._try_restore_redis() is True

    _START_SAVE_WORKER(mgr._repo)
    try:
        mgr._rds_save_queue.put("save_playlist")
        sleep(0.15)
        assert mgr._rds_save_queue.empty(), "自动保存信号必须实际被消费"
        assert json.loads(storage.get(PLAYLIST_RDS_FULL_KEY)) == original
        assert storage.hgetall(PLAYLIST_RDS_HISTORY_KEY) == {}
    finally:
        mgr._repo._save_greenlet.kill()

    assert set(mgr.get_playlist()) == {"existing"}
    mgr._playlist_raw["existing"]["name"] = "edited after recovery"
    assert mgr._repo.save() is True
    assert json.loads(storage.get(PLAYLIST_RDS_FULL_KEY))["existing"]["name"] == "edited after recovery"


def test_failed_reload_keeps_last_good_memory_and_blocks_saves(storage, monkeypatch):
    original = collection()
    storage.set(PLAYLIST_RDS_FULL_KEY, json.dumps(original))
    mgr = pm.PlaylistMgr()
    snapshot = mgr._playlist_raw
    monkeypatch.setattr(rds_mgr, "get", MagicMock(side_effect=ConnectionError("offline")))

    assert mgr.reload() == -1
    assert mgr._playlist_raw is snapshot
    assert mgr._repo.save(swallow_errors=True) is False
    assert json.loads(storage.get(PLAYLIST_RDS_FULL_KEY)) == original
    with pytest.raises(RuntimeError, match="读取失败"):
        mgr.get_playlist()


@pytest.mark.parametrize("bad_payload", ["not json", "null", "[]", '{"broken": null}', ""])
def test_invalid_data_does_not_replace_memory_or_get_saved(storage, bad_payload):
    storage.set(PLAYLIST_RDS_FULL_KEY, json.dumps(collection()))
    mgr = pm.PlaylistMgr()
    snapshot = mgr._playlist_raw
    storage.set(PLAYLIST_RDS_FULL_KEY, bad_payload)

    assert mgr.reload() == -1
    assert mgr._playlist_raw is snapshot
    assert mgr._repo.save(swallow_errors=True) is False
    assert storage.get(PLAYLIST_RDS_FULL_KEY) == bad_payload.encode()


def test_edits_while_redis_is_unavailable_are_rejected_without_changing_memory(
    storage, monkeypatch, tmp_path
):
    fallback(monkeypatch, tmp_path)
    mgr = pm.PlaylistMgr()

    assert mgr.save_playlist(collection("new")) == -1
    assert mgr.update_single_playlist(collection("new")["new"]) == -1
    assert mgr._playlist_raw == {}
    assert storage.get(PLAYLIST_RDS_FULL_KEY) is None


def test_first_edit_after_recovery_reloads_before_merging(storage, monkeypatch, tmp_path):
    storage.set(PLAYLIST_RDS_FULL_KEY, json.dumps(collection()))
    fallback(monkeypatch, tmp_path)
    mgr = pm.PlaylistMgr()
    assert rds_mgr._try_restore_redis() is True

    assert mgr.update_single_playlist(collection("new")["new"]) == 0
    assert set(json.loads(storage.get(PLAYLIST_RDS_FULL_KEY))) == {"existing", "new"}


def test_storage_switch_invalidates_even_a_previously_loaded_snapshot(storage):
    storage.set(PLAYLIST_RDS_FULL_KEY, json.dumps(collection()))
    mgr = pm.PlaylistMgr()
    rds_mgr._client_generation += 1
    storage.set(PLAYLIST_RDS_FULL_KEY, json.dumps(collection("remote")))

    assert mgr._repo.save(swallow_errors=True) is False
    assert set(json.loads(storage.get(PLAYLIST_RDS_FULL_KEY))) == {"remote"}
    assert set(mgr.get_playlist()) == {"remote"}


def test_storage_switch_during_read_is_not_accepted(storage, monkeypatch):
    storage.set(PLAYLIST_RDS_FULL_KEY, json.dumps(collection()))
    mgr = pm.PlaylistMgr()
    snapshot = mgr._playlist_raw

    def switched_read(key):
        raw = storage.get(key)
        rds_mgr._client_generation += 1
        return raw

    monkeypatch.setattr(rds_mgr, "get", switched_read)
    assert mgr.reload() == -1
    assert mgr._playlist_raw is snapshot
    assert mgr._repo.save(swallow_errors=True) is False


def test_reload_setup_error_restores_last_good_collection(storage, monkeypatch):
    storage.set(PLAYLIST_RDS_FULL_KEY, json.dumps(collection()))
    mgr = pm.PlaylistMgr()
    snapshot = mgr._playlist_raw
    storage.set(PLAYLIST_RDS_FULL_KEY, json.dumps(collection("replacement")))
    monkeypatch.setattr(mgr, "_refresh_device_map", MagicMock(side_effect=RuntimeError("device error")))

    assert mgr.reload() == -1
    assert mgr._playlist_raw is snapshot
    assert mgr._repo.save(swallow_errors=True) is False
    assert set(json.loads(storage.get(PLAYLIST_RDS_FULL_KEY))) == {"replacement"}


def test_confirmed_missing_key_allows_creating_a_first_playlist(storage):
    mgr = pm.PlaylistMgr()
    assert mgr.update_single_playlist(collection("first")["first"]) == 0
    assert set(json.loads(storage.get(PLAYLIST_RDS_FULL_KEY))) == {"first"}


def test_intentional_clear_after_successful_load_is_allowed(storage):
    storage.set(PLAYLIST_RDS_FULL_KEY, json.dumps(collection()))
    mgr = pm.PlaylistMgr()

    assert mgr.save_playlist({}) == 0
    assert json.loads(storage.get(PLAYLIST_RDS_FULL_KEY)) == {}


def test_explicit_local_storage_remains_writable(storage, monkeypatch, tmp_path):
    local = fallback(monkeypatch, tmp_path)
    monkeypatch.setenv("REDIS_ENABLED", "false")
    mgr = pm.PlaylistMgr()

    assert mgr.save_playlist(collection()) == 0
    assert json.loads(local.get(PLAYLIST_RDS_FULL_KEY)) == collection()


def test_rejected_storage_write_does_not_report_success_or_write_history(storage, monkeypatch):
    mgr = pm.PlaylistMgr()
    monkeypatch.setattr(rds_mgr, "set", lambda *args: False)

    assert mgr.update_single_playlist(collection("new")["new"]) == -1
    assert storage.hgetall(PLAYLIST_RDS_HISTORY_KEY) == {}
