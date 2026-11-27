from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json

import pytest
from sqlalchemy import create_engine
from core.db import playlist_store as store
from core.services.playlist.calendar_rules import normalize, validate_conflicts, calendar_events


def playlist(identifier='a', **updates):
    raw = {'id': identifier, 'name': identifier, 'device': {'type': 'mi', 'did': 'speaker', 'address': '10.0.0.1'},
           'mode': 'calendar', 'status': 1, 'start_date': '2026-11-01', 'end_date': '2026-11-02',
           'start_time': '23:30:00', 'playlist': [{'uri': 'track', 'duration': 3600}], 'pre_list': [],
           'schedule': {'duration': 0}}
    raw.update(updates)
    return normalize(raw)


@pytest.fixture
def engine(tmp_path):
    e = create_engine('sqlite:///'+str(tmp_path/'playlists.db'))
    store.ensure(e)
    store.migrate(e, {})
    yield e
    e.dispose()


def test_status_legacy_and_mismatched_updates():
    old = normalize({'id': 'x', 'schedule': {'enabled': 0}})
    row = normalize({'schedule': {'enabled': 1, 'cron': '0 7 * * *'}}, old)
    assert row['status'] == row['schedule']['enabled'] == 1
    assert normalize({'status': 0}, row)['schedule']['enabled'] == 0
    assert normalize({'status': 1, 'schedule': {'enabled': 0}}, old)['schedule']['enabled'] == 1


def test_calendar_uses_only_persisted_dates_and_time():
    row = normalize({'id': 'w', 'status': 1, 'schedule': {'cron': '0 0,30 7 * * 1', 'duration': 10}})
    assert row['start_time'] is None
    assert calendar_events({'w': row}, '2026-11-02', '2026-11-03') == []
    row = normalize({'schedule': {'cron': '0 30 8 * * 1'}}, row)
    assert row['start_time'] == '08:30:00'
    events = calendar_events({'w': row}, '2026-11-02', '2026-11-03')
    assert [event['start'][:19] for event in events] == ['2026-11-02T08:30:00', '2026-11-03T08:30:00']
    assert all(event['occurrence_count'] == 1 for event in events)


def test_calendar_inclusive_end_cross_day_and_adjacent():
    a = playlist()
    b = playlist('b', start_date='2026-11-03', end_date='2026-11-03', start_time='00:20:00')
    with pytest.raises(ValueError, match='重叠'):
        validate_conflicts({'a': a, 'b': b})
    b['start_time'] = '00:30:00'
    validate_conflicts({'a': a, 'b': b})
    assert len(calendar_events({'a': a}, '2026-11-01', '2026-11-03')) == 2
    b['status'] = 0
    validate_conflicts({'a': a, 'b': b})


def test_weekly_calendar_conflict_and_schedule_duration_priority():
    a = playlist(start_date='2026-11-02', end_date='2026-11-02', start_time='07:20:00')
    w = normalize({'id': 'w', 'status': 1, 'device': a['device'], 'playlist': [],
                   'schedule': {'cron': '0 0 7 * * 1-5', 'duration': 30}})
    with pytest.raises(ValueError, match='重叠'):
        validate_conflicts({'a': a, 'w': w})
    a['start_time'] = '07:30:00'
    validate_conflicts({'a': a, 'w': w})
    assert playlist(schedule={'duration': 10})['length_seconds'] == 600


def test_unknown_duration_cannot_enable_calendar():
    with pytest.raises(ValueError, match='时长'):
        playlist(playlist=[{'uri': 'unknown'}])
    assert playlist(status=0, playlist=[{'uri': 'unknown'}])['length_seconds'] is None


def test_weekly_unknown_non_scheduled_weekdays_do_not_block_calendar():
    a = playlist(start_date='2026-11-02', end_date='2026-11-02', start_time='10:00:00')
    pre_lists = [[{'uri': 'monday', 'duration': 60}]] + [[] for _ in range(6)]
    w = normalize({'id': 'w', 'status': 1, 'device': a['device'], 'pre_lists': pre_lists,
                   'schedule': {'cron': '0 0 7 * * 1'}})
    validate_conflicts({'a': a, 'w': w})
    w = normalize({'schedule': {'cron': '0 0 7 * * *'}}, w)
    with pytest.raises(ValueError, match='未知'):
        validate_conflicts({'a': a, 'w': w})


def test_calendar_ignores_dense_or_invalid_cron():
    row = normalize({'id': 'w', 'status': 1, 'schedule': {'cron': '* * 7 * * 1-5', 'duration': 20}})
    assert calendar_events({'w': row}, '2026-11-02', '2026-11-02') == []
    row['start_time'] = '07:00:00'
    row['schedule']['cron'] = 'not a valid cron'
    events = calendar_events({'w': row}, '2026-11-02', '2026-11-02')
    assert len(events) == 1 and events[0]['occurrence_count'] == 1
    assert events[0]['start'] == '2026-11-02T07:00:00+08:00'


def test_calendar_excludes_occurrence_ending_exactly_at_range_start():
    a = playlist(start_date='2026-11-01', end_date='2026-11-01', start_time='23:00:00')
    assert calendar_events({'a': a}, '2026-11-02', '2026-11-02') == []


def test_atomic_conflict_validation_rolls_back(engine):
    a = playlist()
    first = store.save(engine, {}, {}, patch=a)
    with pytest.raises(ValueError, match='重叠'):
        store.save(engine, {}, first, patch=playlist('b'))
    assert set(store.load(engine)) == {'a'}


def test_two_concurrent_creates_cannot_claim_same_device(engine):
    def save(identifier):
        try:
            store.save(engine, {}, {}, patch=playlist(identifier))
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(save, ['a', 'b']))
    assert sum(result) == 1


def test_background_save_does_not_overwrite_new_config(engine):
    baseline = store.save(engine, {}, {}, patch=playlist())
    store.save(engine, {}, baseline, patch={'id': 'a', 'name': 'new name'})
    proposed = deepcopy(baseline)
    proposed['a']['isPlaying'] = True
    result = store.save(engine, proposed, baseline)
    assert result['a']['name'] == 'new name' and result['a']['isPlaying']
    with pytest.raises(ValueError, match='变化'):
        store.save(engine, proposed, baseline, replace=True)


def test_stale_edit_rejected_and_runtime_save_keeps_revision(engine):
    baseline = store.save(engine, {}, {}, patch=playlist())
    revision = baseline['a']['_revision']
    proposed = deepcopy(baseline)
    proposed['a']['current_index'] = 1
    result = store.save(engine, proposed, baseline)
    assert result['a']['_revision'] == revision
    store.save(engine, {}, {}, patch={'id': 'a', 'name': 'new', '_revision': revision})
    with pytest.raises(ValueError, match='其他请求'):
        store.save(engine, {}, {}, patch={'id': 'a', 'name': 'stale', '_revision': revision})


def test_history_limited_to_ten(engine):
    for i in range(12):
        store.save(engine, {}, {}, patch={'id': 'x', 'name': str(i), 'schedule': {'enabled': 0}})
    assert len(store.history(engine, 100)) == 10


def test_single_delete_preserves_concurrently_added_rows(engine):
    initial = store.save(engine, {}, {}, patch=playlist())
    store.save(engine, {}, {}, patch={'id': 'new-weekly', 'name': 'new'})
    result = store.save(engine, {}, initial, deletion={'id': 'a', '_revision': initial['a']['_revision']})
    assert set(result) == {'new-weekly'}
    assert store.load(engine)['new-weekly']['name'] == 'new'


def test_stale_delete_rolls_back_without_removing_other_edits(engine):
    initial = store.save(engine, {}, {}, patch=playlist())
    store.save(engine, {}, {}, patch={'id': 'a', 'name': 'edited'})
    with pytest.raises(ValueError, match='其他请求'):
        store.save(engine, {}, initial, deletion={'id': 'a', '_revision': initial['a']['_revision']})
    assert store.load(engine)['a']['name'] == 'edited'


def test_stale_update_cannot_recreate_deleted_playlist(engine):
    initial = store.save(engine, {}, {}, patch=playlist())
    store.save(engine, {}, {}, deletion={'id': 'a', '_revision': initial['a']['_revision']})
    with pytest.raises(ValueError, match='不存在'):
        store.save(engine, {}, {}, patch=initial['a'])
    assert store.load(engine) == {}


@pytest.mark.parametrize('replace', [False, True])
def test_configuration_save_preserves_current_playback_state(engine, replace):
    baseline = store.save(engine, {}, {}, patch=playlist())
    playing = deepcopy(baseline)
    playing['a'].update(isPlaying=True, current_index=3, duration_timer_at='2026-11-03 00:30:00')
    store.save(engine, playing, baseline)
    stale_form = deepcopy(baseline)
    stale_form['a'].update(name='new name', isPlaying=False, current_index=0)
    if replace:
        result = store.save(engine, stale_form, baseline, replace=True)
    else:
        result = store.save(engine, {}, baseline, patch=stale_form['a'])
    assert result['a']['name'] == 'new name'
    assert result['a']['isPlaying'] is True and result['a']['current_index'] == 3
    assert result['a']['duration_timer_at'] == '2026-11-03 00:30:00'


def test_migration_preserves_payload_and_is_idempotent(tmp_path):
    engine = create_engine('sqlite:///'+str(tmp_path/'migration.db'))
    store.ensure(engine)
    with pytest.raises(RuntimeError, match='迁移'):
        store.load(engine)
    source = {'x': {'id': 'x', 'custom': {'keep': 1}, 'schedule': {'enabled': 1, 'cron': ''}}}
    original = deepcopy(source)
    assert store.migrate(engine, source)
    assert store.load(engine)['x']['custom'] == {'keep': 1}
    assert not store.migrate(engine, source)
    assert source == original
    with pytest.raises(ValueError, match='不同快照'):
        store.migrate(engine, {})


def test_db_mgr_routes_playlist_operations_to_its_app_database(tmp_path):
    from flask import Flask
    from core.db.db_mgr import DbMgr
    from core.db import db_obj
    app = Flask('playlist-db-integration', instance_path=str(tmp_path))
    manager = DbMgr()
    manager.init(app)
    with pytest.raises(RuntimeError, match='迁移'):
        manager.playlist_operation('load')
    manager.playlist_operation('migrate', {})
    result = manager.playlist_operation('save', {}, {}, patch={'id': 'x', 'name': 'DB'})
    assert result['x']['name'] == 'DB'
    assert (tmp_path/'data.db').exists()
    with app.app_context():
        db_obj.session.remove()
        db_obj.engine.dispose()


def test_calendar_query_filters_columns_before_payload_decode(engine):
    state = store.save(engine, {}, {}, patch=playlist(start_date='2026-11-01', end_date='2026-11-01', start_time='09:00:00'))
    from sqlalchemy import text
    with engine.begin() as c:
        for identifier, status, day in [('future', 1, '2040-01-01'), ('expired', 1, '2000-01-01'), ('disabled', 0, '2026-11-01')]:
            c.execute(text("""INSERT INTO t_playlist(id,mode,name,status,start_date,end_date,start_time,length_seconds,
                create_time,updated_time,payload) VALUES(:id,'calendar',:id,:status,:day,:day,'09:00:00',60,'now','now','invalid json')"""),
                {'id': identifier, 'status': status, 'day': day})
    events = store.calendar(engine, '2026-11-01', '2026-11-01')
    assert [event['id'] for event in events] == ['a']


def test_calendar_query_uses_db_dates_instead_of_payload_dates(engine):
    store.save(engine, {}, {}, patch=playlist(start_date='2026-01-01', end_date='2026-01-01', start_time='09:00:00'))
    from sqlalchemy import text
    with engine.begin() as c:
        c.execute(text("UPDATE t_playlist SET start_date='2026-11-01',end_date='2026-11-01',start_time='10:30:00' WHERE id='a'"))
    events = store.calendar(engine, '2026-11-01', '2026-11-01')
    assert len(events) == 1
    assert events[0]['start'] == '2026-11-01T10:30:00+08:00'
    assert store.calendar(engine, '2026-01-01', '2026-01-01') == []


def test_calendar_query_includes_cross_day_and_excludes_exact_midnight_end(engine):
    state = store.save(engine, {}, {}, patch=playlist())
    events = store.calendar(engine, '2026-11-03', '2026-11-03')
    assert len(events) == 1 and events[0]['start'].startswith('2026-11-02T23:30:00')
    store.save(engine, {}, state, patch={'id': 'a', 'start_time': '23:00:00'})
    assert store.calendar(engine, '2026-11-03', '2026-11-03') == []


def test_calendar_query_includes_long_single_day_playback(engine):
    store.save(engine, {}, {}, patch=playlist(start_date='2026-11-01', end_date='2026-11-01',
        start_time='23:30:00', playlist=[{'uri': 'long', 'duration': 3 * 86400}]))
    events = store.calendar(engine, '2026-11-04', '2026-11-04')
    assert len(events) == 1 and events[0]['start'].startswith('2026-11-01')


def test_weekly_calendar_query_clamps_cron_to_db_dates(engine):
    from sqlalchemy import text
    row = normalize({'id': 'w', 'status': 1, 'playlist': [{'uri': 'main', 'duration': 60}],
                     'schedule': {'cron': '0 0 7 * * *'}})
    store.save(engine, {}, {}, patch=row)
    with engine.begin() as c:
        c.execute(text("UPDATE t_playlist SET start_date='2026-11-03',end_date='2026-11-04' WHERE id='w'"))
    events = store.calendar(engine, '2026-11-01', '2026-11-05')
    assert [event['start'][:10] for event in events] == ['2026-11-03', '2026-11-04']


def test_weekly_calendar_query_carries_varying_weekday_duration(engine):
    from sqlalchemy import text
    row = normalize({'id': 'w', 'status': 1, 'playlist': [{'uri': 'main', 'duration': 60}],
        'pre_lists': [[] for _ in range(6)] + [[{'uri': 'sunday', 'duration': 7200}]],
        'schedule': {'cron': '0 30 23 * * 0'}})
    assert row['length_seconds'] is None
    store.save(engine, {}, {}, patch=row)
    with engine.begin() as c:
        c.execute(text("UPDATE t_playlist SET start_date='2026-11-01',end_date='2026-11-01' WHERE id='w'"))
    events = store.calendar(engine, '2026-11-02', '2026-11-02')
    assert len(events) == 1 and events[0]['length_seconds'] == 7260


@pytest.mark.parametrize('start,end', [('invalid','2026-11-01'), (None,'2026-11-01'),
    ('2026-11-03','2026-11-01'), ('2026-01-01','2026-03-04'), ('9999-12-31','9999-12-31')])
def test_calendar_query_rejects_invalid_range_before_db_read(engine, start, end):
    from sqlalchemy import event
    statements = []
    def record(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)
    event.listen(engine, 'before_cursor_execute', record)
    try:
        with pytest.raises(ValueError, match='1–62'):
            store.calendar(engine, start, end)
        assert statements == []
    finally:
        event.remove(engine, 'before_cursor_execute', record)


def test_calendar_query_does_not_parse_or_expand_cron(engine, monkeypatch):
    from sqlalchemy import text
    from core.services.playlist import calendar_rules
    row = normalize({'id': 'w', 'status': 1, 'schedule': {'cron': '* * 7 * * *', 'duration': 20}})
    store.save(engine, {}, {}, patch=row)
    with engine.begin() as c:
        c.execute(text("UPDATE t_playlist SET start_time='07:00:00' WHERE id='w'"))
    def forbidden(*_args, **_kwargs):
        raise AssertionError('calendar reads must not parse cron or enumerate trigger occurrences')
    monkeypatch.setattr(calendar_rules, 'cron_trigger', forbidden)
    monkeypatch.setattr(calendar_rules, 'occurrences', forbidden)
    events = store.calendar(engine, '2026-11-01', '2027-01-01')
    assert len(events) == 62
    assert all(event['occurrence_count'] == 1 for event in events)
    assert events[-1]['start'] == '2027-01-01T07:00:00+08:00'


def test_calendar_query_requires_migration(tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path / 'not-migrated.db'))
    store.ensure(engine)
    with pytest.raises(RuntimeError, match='迁移'):
        store.calendar(engine, '2026-11-01', '2026-11-01')
    engine.dispose()
