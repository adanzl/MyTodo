"""Explicit one-time migration from a frozen remote Redis export into SQLite.

Run while playlist writes are paused. Default is read-only preview. This tool never
connects Redis or devices; pass the exported snapshot and an explicit DB path.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types

# Load storage/domain modules without starting the application or device managers.
root = Path(__file__).resolve().parent
for name, path in [('core', root/'core'), ('core.db', root/'core/db'),
                   ('core.services', root/'core/services'), ('core.services.playlist', root/'core/services/playlist')]:
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module
from sqlalchemy import create_engine
from core.db.playlist_store import ensure, migrate
from core.services.playlist.calendar_rules import normalize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    raw = args.snapshot.read_bytes()
    snapshot = json.loads(raw)
    rows = snapshot['collection']
    if not isinstance(rows, dict):
        raise ValueError('snapshot.collection must be a dictionary')
    normalized = {k: normalize({**v, 'id': k, 'mode': 'weekly'}, importing=True) for k, v in rows.items()}
    print(json.dumps({'rows': len(rows), 'enabled': sum(v['status'] for v in normalized.values()),
                      'snapshot_sha256': hashlib.sha256(raw).hexdigest(), 'apply': args.apply}))
    if args.apply:
        if not args.db.exists():
            raise ValueError('目标数据库不存在，必须明确选择已备份的数据库')
        engine = create_engine('sqlite:///'+str(args.db.resolve()))
        ensure(engine)
        changed = migrate(engine, rows, snapshot.get('history'))
        print('migrated' if changed else 'already migrated; unchanged')


if __name__ == '__main__':
    main()
