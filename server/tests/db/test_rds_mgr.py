import json

import fakeredis
import pytest

import core.db.rds_mgr as rds_mgr


@pytest.fixture(autouse=True)
def rds_mgr_env(monkeypatch):
    """Provides a mocked rds_mgr environment for testing."""
    fake_redis_client = fakeredis.FakeRedis()
    monkeypatch.setattr(rds_mgr, 'rds', fake_redis_client)
    # Clear the fake redis before each test
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
