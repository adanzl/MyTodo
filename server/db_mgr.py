import logging
import sqlite3
import traceback

log = logging.getLogger(__name__)

DB_NAME = "data.db"
TABLE_SAVE = "t_user_save"
TABLE_PIC = "t_user_pic"


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
    create_t_user_pic_sql = f'''
        CREATE TABLE IF NOT EXISTS {TABLE_PIC} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT
        );
    '''
    cur.execute(create_t_user_save_sql)
    cur.execute(create_t_user_pic_sql)
    conn.commit()
    cur.close()


def get_save(id) -> str:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT * FROM {TABLE_SAVE} WHERE id=?", (id))
        result = cur.fetchone()
        if result:
            data = result[2]
        else:
            data = "{}"
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return {"code": -1, "msg": 'error ' + str(e)}
    finally:
        cur.close()
    return {"code": 0, "msg": "ok", "data": data}


def set_save(id, user_name, data) -> str:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        if id:
            cur.execute(
                f"""
                INSERT INTO {TABLE_SAVE} (id, user_name,data) VALUES (?,?,?)
                ON CONFLICT(id) DO UPDATE SET data=?;
                """, (id, user_name, data, data))
        else:
            cur.execute(
                f"""
                INSERT INTO {TABLE_SAVE} (user_name,data) VALUES (?,?);
                """, (user_name, data))
        conn.commit()
        id = cur.lastrowid
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return {"code": -1, "msg": 'error ' + str(e)}
    finally:
        cur.close()
    return {"code": 0, "msg": "ok", "data": id}


def get_pic(id) -> str:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT * FROM {TABLE_PIC} WHERE id=?", (id))
        result = cur.fetchone()
        if result:
            data = result[1]
        else:
            data = ""
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return {"code": -1, "msg": 'error ' + str(e)}
    finally:
        cur.close()
    return {"code": 0, "msg": "ok", "data": data}


def set_pic(id, data) -> str:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        if id:
            cur.execute(
                f"""
                INSERT INTO {TABLE_PIC} (id,data) VALUES (?,?)
                ON CONFLICT(id) DO UPDATE SET data=?;
                """, (id, data, data))
        else:
            cur.execute(f"""
                INSERT INTO {TABLE_PIC} (data) VALUES (?);
                """, (data, ))
        conn.commit()
        id = cur.lastrowid
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return {"code": -1, "msg": 'error ' + str(e)}
    finally:
        cur.close()
    return {"code": 0, "msg": "ok", "data": id}


def del_pic(id) -> str:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(f"""
            DELETE FROM {TABLE_PIC} WHERE id=?;
            """, (id))
        conn.commit()
        cnt = cur.rowcount
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return {"code": -1, "msg": 'error ' + str(e)}
    finally:
        cur.close()
    return {"code": 0, "msg": "ok", "data": cnt}
