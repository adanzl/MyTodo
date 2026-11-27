"""SQLite playlist persistence. All callers enter through db_mgr."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from sqlalchemy import text
from core.services.playlist.calendar_rules import normalize, validate_conflicts, RUNTIME_FIELDS


def ensure(engine):
    with engine.begin() as c:
        c.execute(text('''CREATE TABLE IF NOT EXISTS t_playlist (
            id TEXT PRIMARY KEY, mode TEXT NOT NULL, name TEXT NOT NULL,
            device_type TEXT, device_address TEXT, device_did TEXT, device_name TEXT, device_key TEXT,
            status INTEGER NOT NULL CHECK(status IN (0,1)), start_date TEXT, end_date TEXT, start_time TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0, length_seconds REAL, create_time TEXT NOT NULL,
            updated_time TEXT NOT NULL, payload TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1)'''))
        c.execute(text('CREATE INDEX IF NOT EXISTS idx_playlist_device ON t_playlist(device_key,status,mode)'))
        c.execute(text('''CREATE TABLE IF NOT EXISTS t_playlist_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL DEFAULT 'snapshot',
            create_time TEXT NOT NULL, payload TEXT NOT NULL)'''))


def _read(c):
    rows = c.execute(text('SELECT id,payload,status,revision FROM t_playlist ORDER BY sort_order,id')).mappings()
    result = {}
    for row in rows:
        value = json.loads(row['payload'])
        value['status'] = row['status']
        value.setdefault('schedule', {})['enabled'] = row['status']
        value['_revision'] = row['revision']
        result[row['id']] = value
    return result


def load(engine):
    with engine.connect() as c:
        if not c.execute(text("SELECT 1 FROM t_playlist_history WHERE kind='migration' LIMIT 1")).scalar():
            raise RuntimeError('播放列表 DB 尚未完成一次性迁移，请运行迁移工具')
        return _read(c)


def configuration(value):
    result = {k: deepcopy(v) for k, v in value.items() if k not in RUNTIME_FIELDS | {'_revision', 'updated_time', 'updatedAt', 'length_seconds', 'weekday_lengths'}}
    return result


def content_configuration(value):
    result = configuration(value)
    def strip(items):
        for item in items:
            if isinstance(item, dict):
                item.pop('duration', None)
    strip(result.get('playlist', []))
    strip(result.get('pre_list', []))
    for items in result.get('pre_lists', []):
        strip(items)
    return result


def _normalize_edit(value, previous=None):
    # Configuration forms must not replay old playback cursors or timer state.
    return normalize({k: v for k, v in value.items() if k not in RUNTIME_FIELDS}, previous)


def _write(c, values, previous):
    now = datetime.now().isoformat(timespec='microseconds')
    for identifier, value in values.items():
        value = deepcopy(value)
        old = previous.get(identifier, {})
        revision = old.get('_revision', 0) + int(configuration(value) != configuration(old))
        if old and {k: v for k, v in value.items() if k != '_revision'} == {k: v for k, v in old.items() if k != '_revision'}:
            continue
        value.pop('_revision', None)
        device = value.get('device') or {}
        fields = {'id': identifier, 'mode': value['mode'], 'name': value.get('name', ''),
                  'device_type': device.get('type'), 'device_address': device.get('address'),
                  'device_did': device.get('did'), 'device_name': device.get('name'),
                  'device_key': value.get('device_key'), 'status': value['status'],
                  'start_date': value.get('start_date'), 'end_date': value.get('end_date'),
                  'start_time': value.get('start_time'), 'sort_order': value.get('order', 0) or 0,
                  'length_seconds': value.get('length_seconds'), 'create_time': value.get('create_time') or now,
                  'updated_time': now, 'payload': json.dumps(value, ensure_ascii=False), 'revision': revision}
        c.execute(text('INSERT INTO t_playlist (' + ','.join(fields) + ') VALUES (' +
                       ','.join(':'+k for k in fields) + ') ON CONFLICT(id) DO UPDATE SET ' +
                       ','.join(k+'=excluded.'+k for k in fields if k not in ('id', 'create_time'))), fields)
    for identifier in previous.keys() - values.keys():
        c.execute(text('DELETE FROM t_playlist WHERE id=:id'), {'id': identifier})
    c.execute(text("INSERT INTO t_playlist_history(kind,create_time,payload) VALUES('snapshot',:now,:payload)"),
              {'now': now, 'payload': json.dumps(values, ensure_ascii=False)})
    c.execute(text("DELETE FROM t_playlist_history WHERE kind='snapshot' AND id NOT IN (SELECT id FROM t_playlist_history WHERE kind='snapshot' ORDER BY id DESC LIMIT 10)"))


def save(engine, proposed, baseline, *, replace=False, patch=None, deletion=None, runtime=None):
    with engine.connect() as c:
        # Reserve the SQLite writer before reading any conflict inputs.
        c.exec_driver_sql('BEGIN IMMEDIATE')
        try:
            current = _read(c)
            merged = deepcopy(current)
            if deletion is not None:
                identifier = str(deletion['id'])
                if identifier not in current:
                    raise ValueError('播放列表已不存在，请刷新后重试')
                if deletion.get('_revision') is not None and deletion['_revision'] != current[identifier]['_revision']:
                    raise ValueError('播放列表已被其他请求修改，请刷新后重试')
                merged.pop(identifier)
            elif patch is not None:
                identifier = str(patch['id'])
                if identifier not in current and patch.get('_revision') is not None:
                    raise ValueError('播放列表已不存在，请刷新后重试')
                if identifier in current and patch.get('_revision') is not None and patch['_revision'] != current[identifier]['_revision']:
                    raise ValueError('播放列表已被其他请求修改，请刷新后重试')
                merged[identifier] = _normalize_edit(patch, current.get(identifier))
            elif replace:
                if {k: v.get('_revision') for k, v in baseline.items()} != {k: v.get('_revision') for k, v in current.items()}:
                    raise ValueError('播放列表集合已变化，请刷新后重试')
                for identifier, value in proposed.items():
                    if identifier in current and value.get('_revision') is not None and value['_revision'] != current[identifier]['_revision']:
                        raise ValueError('播放列表已被其他请求修改，请刷新后重试')
                merged = {str(k): _normalize_edit({**v, 'id': str(k)}, current.get(str(k))) for k, v in proposed.items()}
            else:
                # Background state saves merge field-level deltas; never replay old config.
                for identifier, value in proposed.items():
                    if identifier not in current or identifier not in baseline:
                        continue
                    if content_configuration(value) != content_configuration(baseline[identifier]):
                        if baseline[identifier].get('_revision') != current[identifier].get('_revision'):
                            raise ValueError('后台配置变更遇到并发编辑，已停止覆盖')
                        merged[identifier] = normalize(value, current[identifier])
                        continue
                    for key in RUNTIME_FIELDS:
                        if value.get(key) != baseline[identifier].get(key):
                            if key in value:
                                merged[identifier][key] = deepcopy(value[key])
                            else:
                                merged[identifier].pop(key, None)
                    # Duration discovery only fills unchanged source items.
                    def fill(now_items, before_items, new_items):
                        for now_item, before, new in zip(now_items, before_items, new_items):
                            if now_item.get('uri') == before.get('uri') == new.get('uri') and not now_item.get('duration') and new.get('duration'):
                                now_item['duration'] = new['duration']
                    fill(merged[identifier].get('playlist', []), baseline[identifier].get('playlist', []), value.get('playlist', []))
                    for key in ('pre_lists',):
                        for ni, bi, vi in zip(merged[identifier].get(key, []), baseline[identifier].get(key, []), value.get(key, [])):
                            fill(ni, bi, vi)
                    fill(merged[identifier].get('pre_list', []), baseline[identifier].get('pre_list', []), value.get('pre_list', []))
                    merged[identifier] = normalize(merged[identifier])
            if runtime is not None and (patch is not None or replace or deletion is not None):
                # Preserve server-side playback changes that have not reached the save worker yet.
                for identifier, live in runtime.items():
                    if identifier not in merged or identifier not in baseline:
                        continue
                    for key in RUNTIME_FIELDS:
                        if live.get(key) != baseline[identifier].get(key):
                            if key in live:
                                merged[identifier][key] = deepcopy(live[key])
                            else:
                                merged[identifier].pop(key, None)
            validate_conflicts(merged)
            _write(c, merged, current)
            result = _read(c)
            c.commit()
            return result
        except BaseException:
            c.rollback()
            raise


def history(engine, limit):
    with engine.connect() as c:
        rows = c.execute(text("SELECT id,create_time,payload FROM t_playlist_history WHERE kind='snapshot' ORDER BY id DESC LIMIT :limit"), {'limit': min(10, max(1, limit))}).mappings()
        return {row['create_time']+'#'+str(row['id']): row['payload'] for row in rows}


def migrate(engine, source, history_payloads=None):
    digest = hashlib.sha256(json.dumps(source, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    with engine.connect() as c:
        c.exec_driver_sql('BEGIN IMMEDIATE')
        try:
            prior = c.execute(text("SELECT payload FROM t_playlist_history WHERE kind='migration' LIMIT 1")).scalar()
            if prior:
                if json.loads(prior)['sha256'] != digest:
                    raise ValueError('DB 已从不同快照迁移，禁止覆盖')
                c.rollback()
                return False
            if c.execute(text('SELECT count(*) FROM t_playlist')).scalar():
                raise ValueError('目标表非空，禁止迁移覆盖')
            values = {str(k): normalize({**v, 'id': str(k), 'mode': 'weekly'}, importing=True) for k, v in source.items()}
            _write(c, values, {})
            c.execute(text("INSERT INTO t_playlist_history(kind,create_time,payload) VALUES('migration',:now,:payload)"),
                      {'now': datetime.now().isoformat(), 'payload': json.dumps({'sha256': digest, 'count': len(values)})})
            if history_payloads:
                c.execute(text("DELETE FROM t_playlist_history WHERE kind='snapshot'"))
                for timestamp, payload in sorted(history_payloads.items())[-10:]:
                    if not isinstance(json.loads(payload), dict):
                        raise ValueError('迁移历史格式错误')
                    c.execute(text("INSERT INTO t_playlist_history(kind,create_time,payload) VALUES('snapshot',:now,:payload)"), {'now': timestamp, 'payload': payload})
            # A normalized readback must preserve every source ID before commit.
            if set(_read(c)) != set(source):
                raise ValueError('迁移 ID 校验失败')
            c.commit()
            return True
        except BaseException:
            c.rollback()
            raise
