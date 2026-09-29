import json

import pytest

from core.chat import tts_cache


@pytest.fixture
def patch_rds(monkeypatch):
    store: dict[str, bytes | str] = {}

    def _set(key, value):
        if isinstance(value, str):
            store[key] = value.encode("utf-8")
        else:
            store[key] = value
        return True

    def _get(key):
        return store.get(key)

    def _exists(key):
        return 1 if key in store else 0

    def _append(key, value):
        cur = store.get(key, b"")
        if isinstance(cur, str):
            cur = cur.encode("utf-8")
        if isinstance(value, str):
            value = value.encode("utf-8")
        store[key] = cur + value
        return len(store[key])

    def _get_str(key):
        v = store.get(key, b"")
        if isinstance(v, bytes):
            return v.decode("utf-8")
        return str(v)

    def _setex(key, _ttl, value):
        return _set(key, value)

    monkeypatch.setattr(tts_cache.rds_mgr, "set", _set)
    monkeypatch.setattr(tts_cache.rds_mgr, "get", _get)
    monkeypatch.setattr(tts_cache.rds_mgr, "exists", _exists)
    monkeypatch.setattr(tts_cache.rds_mgr, "append_value", _append)
    monkeypatch.setattr(tts_cache.rds_mgr, "get_str", _get_str)
    monkeypatch.setattr(tts_cache.rds_mgr, "setex", _setex)
    return store


def test_incomplete_cache_not_served(patch_rds):
    session = tts_cache.begin_session("m1", "hello", "longwan_v3", 1.0)
    tts_cache.append_audio(session, b"abc")
    assert tts_cache.get_complete_audio("m1", "hello", "longwan_v3", 1.0) is None


def test_complete_cache_hit(patch_rds):
    session = tts_cache.begin_session("m1", "hello", "longwan_v3", 1.1)
    tts_cache.append_audio(session, b"audio-bytes")
    tts_cache.finalize_session(session)
    data = tts_cache.get_complete_audio("m1", "hello", "longwan_v3", 1.1)
    assert data == b"audio-bytes"


def test_speed_or_text_change_misses_cache(patch_rds):
    session = tts_cache.begin_session("m1", "hello", "longwan_v3", 1.0)
    tts_cache.append_audio(session, b"x")
    tts_cache.finalize_session(session)
    assert tts_cache.get_complete_audio("m1", "hello", "longwan_v3", 1.1) is None
    assert tts_cache.get_complete_audio("m1", "hello world", "longwan_v3", 1.0) is None


def test_abort_clears_served_audio(patch_rds):
    session = tts_cache.begin_session("m1", "hello", "longwan_v3", 1.0)
    tts_cache.append_audio(session, b"partial")
    tts_cache.abort_session(session)
    assert tts_cache.get_complete_audio("m1", "hello", "longwan_v3", 1.0) is None
    meta_key = session["meta_key"]
    meta = json.loads(patch_rds[meta_key].decode("utf-8"))
    assert meta.get("complete") is False
