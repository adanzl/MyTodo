import logging
import sqlite3
import traceback

log = logging.getLogger(__name__)

DB_NAME = "data.db"
TABLE_SAVE = "t_user_save"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    create_t_user_save_sql = f'''
    CREATE TABLE IF NOT EXISTS {TABLE_SAVE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT NOT NULL,
        data TEXT
    );
    '''
    cur.execute(create_t_user_save_sql)
    conn.commit()
    cur.close()


def get_save(id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT * FROM {TABLE_SAVE} WHERE id=?", (id))
        result = cur.fetchone()
        if result:
            return result[2]
        else:
            return "{}"
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return "{}"
    finally:
        cur.close()


def set_save(id, user_name, data):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            INSERT INTO {TABLE_SAVE} (id, user_name,data) VALUES (?,?,?)
            ON CONFLICT(id) DO UPDATE SET data=?;
            """, (id, user_name, data, data))
        conn.commit()
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return 'error ' + str(e)
    finally:
        cur.close()
    return "ok"
