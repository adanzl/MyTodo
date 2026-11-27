"""DB-only repository readiness, failures and concurrent state saves."""
from copy import deepcopy
from queue import Queue
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text
from core.db import playlist_store
from core.services.playlist.repository import PlaylistRepository, db_mgr


@pytest.fixture
def storage(tmp_path, monkeypatch):
    engine = create_engine('sqlite:///'+str(tmp_path/'playlists.db'))
    playlist_store.ensure(engine)
    playlist_store.migrate(engine, {})
    monkeypatch.setattr(db_mgr, 'playlist_operation',
        lambda op, *args, **kw: getattr(playlist_store, op)(engine, *args, **kw))
    current = {}
    repo = PlaylistRepository(lambda: current, Queue())
    current.update(repo.load_raw())
    yield engine, current, repo
    engine.dispose()


def test_successful_load_authorizes_saves_and_does_not_use_redis(storage, monkeypatch):
    from core.db import rds_mgr
    monkeypatch.setattr(rds_mgr, 'get', Mock(side_effect=AssertionError('Redis read')))
    monkeypatch.setattr(rds_mgr, 'set', Mock(side_effect=AssertionError('Redis write')))
    _, current, repo = storage
    repo.save(patch={'id': 'x', 'name': 'x'})
    assert repo.is_ready and set(current) == {'x'}
    assert set(repo.load_raw()) == {'x'}


def test_failed_load_keeps_repository_unready(storage, monkeypatch):
    _, _, repo = storage
    monkeypatch.setattr(db_mgr, 'playlist_operation', Mock(side_effect=RuntimeError('DB unavailable')))
    with pytest.raises(RuntimeError):
        repo.load_raw()
    assert not repo.is_ready
    assert repo.save(swallow_errors=True) is False


def test_failed_save_does_not_replace_memory(storage, monkeypatch):
    _, current, repo = storage
    repo.save(patch={'id': 'x', 'name': 'before'})
    old = deepcopy(current)
    monkeypatch.setattr(db_mgr, 'playlist_operation', Mock(side_effect=RuntimeError('DB unavailable')))
    with pytest.raises(RuntimeError):
        repo.save(patch={'id': 'x', 'name': 'after'})
    assert current == old and not repo.is_ready


def test_corrupt_payload_is_not_treated_as_empty_collection(storage):
    engine, _, repo = storage
    repo.save(patch={'id': 'x', 'name': 'before'})
    with engine.begin() as c:
        c.execute(text("UPDATE t_playlist SET payload='not JSON' WHERE id='x'"))
    with pytest.raises(ValueError):
        repo.load_raw()
    assert not repo.is_ready


def test_empty_loaded_collection_can_be_replaced(storage):
    _, current, repo = storage
    current['x'] = {'id': 'x', 'name': 'new'}
    repo.save(replace=True)
    assert set(repo.load_raw()) == {'x'}
    current.clear()
    repo.save(replace=True)
    assert repo.load_raw() == {}


def test_stale_full_collection_is_rejected(storage):
    engine, current, repo = storage
    repo.save(patch={'id': 'x', 'name': 'before'})
    playlist_store.save(engine, {}, {}, patch={'id': 'x', 'name': 'concurrent'})
    current['x']['name'] = 'stale'
    with pytest.raises(ValueError, match='变化'):
        repo.save(replace=True)
    assert playlist_store.load(engine)['x']['name'] == 'concurrent'


def test_play_refresh_does_not_advance_unrelated_configuration_baseline(storage):
    engine, current, repo = storage
    repo.save(patch={'id': 'x', 'name': 'before'})
    repo.save(patch={'id': 'y', 'name': 'before'})
    playlist_store.save(engine, {}, {}, patch={'id': 'y', 'name': 'concurrent'})
    repo.refresh_one('x')
    current['x']['current_index'] = 1
    repo.save()
    assert playlist_store.load(engine)['y']['name'] == 'concurrent'


def test_configuration_save_flushes_pending_server_playback_delta(storage):
    engine, current, repo = storage
    repo.save(patch={'id': 'x', 'name': 'before'})
    current['x'].update(isPlaying=True, current_index=3, file_timer_at='2026-11-26 23:00:00')
    repo.save(patch={'id': 'x', 'name': 'after', 'isPlaying': False, 'current_index': 0})
    saved = playlist_store.load(engine)['x']
    assert saved['name'] == 'after' and saved['isPlaying'] is True
    assert saved['current_index'] == 3 and saved['file_timer_at'] == '2026-11-26 23:00:00'
