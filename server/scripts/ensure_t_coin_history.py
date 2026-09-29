#!/usr/bin/env python3
"""在 SQLite 上按 t_score_history 克隆 t_coin_history（幂等）。可在远程 server 目录执行。"""
import os
import sys

_SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_SERVER_ROOT)
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)

from core import create_app
from core.db.db_mgr import db_mgr

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db_mgr.ensure_t_coin_history_table()
    print("t_coin_history OK")
