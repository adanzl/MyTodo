import json

import fakeredis
import pytest

import core.db.rds_mgr as rds_mgr


@pytest.fixture(autouse=True)
def rds_mgr_env(monkeypatch):
    """Provides a mocked rds_mgr environment for testing."""
    fake_redis_client = fakeredis.FakeRedis()
    monkeypatch.setattr(rds_mgr, 'rds', fake_redis_client)
    monkeypatch.setattr(rds_mgr, '_local_store', None)
    monkeypatch.setattr(rds_mgr, 'is_local_fallback', False)
    fake_redis_client.flushall()
    return rds_mgr


def test_set_and_get_str(rds_mgr_env):
    rds_mgr_env.set("mykey", "myvalue")
    assert rds_mgr_env.get_str("mykey") == "myvalue"


def test_get_str_not_found_returns_empty_string(rds_mgr_env):
    assert rds_mgr_env.get_str("nonexistent") == ""


def test_list_operations(rds_mgr_env):
    key = "my_list"
    rds_mgr_env.rpush(key, "a")
    rds_mgr_env.lpush(key, "b")  # List should now be [b, a]

    assert rds_mgr_env.llen(key) == 2
    assert rds_mgr_env.lrange(key, 0, -1) == ["b", "a"]


def test_exists(rds_mgr_env):
    assert not rds_mgr_env.exists("new_key")
    rds_mgr_env.set("new_key", "v")
    assert rds_mgr_env.exists("new_key")


def test_local_json_fallback(tmp_path, monkeypatch):
    """未配置 Redis 时使用本地 JSON 文件存储。"""
    store_path = tmp_path / "rds_local.json"
    monkeypatch.setenv("REDIS_ENABLED", "false")
    monkeypatch.setenv("RDS_LOCAL_FILE", str(store_path))
    monkeypatch.setattr(rds_mgr, "rds", None)
    monkeypatch.setattr(rds_mgr, "is_local_fallback", True)
    monkeypatch.setattr(rds_mgr, "_local_store", rds_mgr._LocalJsonStore(str(store_path)))

    store = rds_mgr._local_store
    store.set("mykey", "myvalue")
    assert rds_mgr.get_str("mykey") == "myvalue"

    rds_mgr.rpush("my_list", "a")
    rds_mgr.lpush("my_list", "b")
    assert rds_mgr.llen("my_list") == 2
    assert rds_mgr.lrange("my_list", 0, -1) == ["b", "a"]

    rds_mgr.hset("my_hash", "f1", "v1")
    assert rds_mgr.hgetall("my_hash") == {"f1": "v1"}
    assert rds_mgr.hlen("my_hash") == 1

    assert store_path.exists()
    persisted = json.loads(store_path.read_text(encoding="utf-8"))
    assert persisted["strings"]["mykey"] == "myvalue"
    assert persisted["lists"]["my_list"] == ["b", "a"]
    assert persisted["hashes"]["my_hash"]["f1"] == "v1"


def test_redis_disabled_when_host_empty(monkeypatch):
    monkeypatch.delenv("REDIS_ENABLED", raising=False)
    monkeypatch.setenv("REDIS_HOST", "")
    assert rds_mgr._redis_enabled_by_config() is False
