import json
import sqlite3
import traceback

from core.log_config import root_logger

log = root_logger()

DB_NAME = "data.db"
TABLE_SAVE = "t_user_save"
TABLE_PIC = "t_user_pic"
TABLE_USER = "t_user"
TABLE_SCORE_HISTORY = "t_score_history"


def init():
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
    create_t_user_sql = f'''
        CREATE TABLE IF NOT EXISTS {TABLE_USER} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            icon TEXT,
            pwd TEXT,
            score INTEGER DEFAULT 0
        );
    '''
    cur.execute(create_t_user_save_sql)
    cur.execute(create_t_user_pic_sql)
    cur.execute(create_t_user_sql)
    conn.commit()
    cur.close()


def set_save(id, user_name, data) -> dict:
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


def get_all_pic(page_num=1, page_size=20) -> dict:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(f"""
            SELECT * FROM {TABLE_PIC} LIMIT ? OFFSET ?;
            """, (page_size, (page_num - 1) * page_size))
        result = cur.fetchall()
        data = [{'id': r[0], 'data': r[1]} for r in result]
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return {"code": -1, "msg": 'error ' + str(e)}
    finally:
        cur.close()
    return {"code": 0, "msg": "ok", "data": data}


def get_data_idx(table, id, idx=1):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT * FROM {table} WHERE id=?", (id, ))
        result = cur.fetchone()
        if result:
            data = result[idx]
            try:
                data = json.loads(data)
            except:
                pass
        else:
            data = "{}"
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return {"code": -1, "msg": 'error ' + str(e)}
    finally:
        cur.close()
    return {"code": 0, "msg": "ok", "data": data}


def get_data(table, id, fields):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT {fields} FROM {table} WHERE id=?", (id, ))
        result = cur.fetchone()
        if result:
            data = dict(zip([col[0] for col in cur.description], result))
        else:
            data = "{}"
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return {"code": -1, "msg": 'error ' + str(e)}
    finally:
        cur.close()
    return {"code": 0, "msg": "ok", "data": data}


def set_data(table, data):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        id = data.get('id')
        fields = ','.join(data.keys())
        values = ','.join(['?'] * len(data))
        set_values = ','.join([f"{k}=?" for k in data.keys()])
        if id:
            cur.execute(
                f"""
                INSERT INTO {table} ({fields}) VALUES ({values})
                ON CONFLICT(id) DO UPDATE SET {set_values};
                """, tuple(list(data.values()) + list(data.values())))
        else:
            cur.execute(f"""
                INSERT INTO {table} ({fields}) VALUES ({values});
                """, tuple(data.values()))
        conn.commit()
        if not id:
            id = cur.lastrowid
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return {"code": -1, "msg": 'error ' + str(e)}
    finally:
        cur.close()
    return {"code": 0, "msg": "ok", "data": id}


def add_score(user_id, value, action, msg):
    '''
        增加积分
    '''
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT score FROM {TABLE_USER} WHERE id=?", (user_id, ))
        pre_score = cur.fetchone()[0]
        cur_score = pre_score + int(value)
        cur.execute(
            f"""
            INSERT INTO {TABLE_SCORE_HISTORY} (user_id, value, action, pre_value, current, msg) VALUES (?,?,?,?,?,?);
            """, (user_id, value, action, pre_score, cur_score, msg))
        cur.execute(
            f"""
            UPDATE {TABLE_USER} SET score=? WHERE id=?;
            """, (cur_score, user_id))
        conn.commit()
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return {"code": -1, "msg": 'error ' + str(e)}
    finally:
        cur.close()
    return {"code": 0, "msg": "ok", "data": cur_score}


def del_data(table, id: int) -> dict:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(f"""
            DELETE FROM {table} WHERE id=?;
            """, (id, ))
        conn.commit()
        cnt = cur.rowcount
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return {"code": -1, "msg": 'error ' + str(e)}
    finally:
        cur.close()
    return {"code": 0, "msg": "ok", "data": cnt}


def query(sql) -> dict:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(sql)
        result = cur.fetchall()
        if result:
            data = result
        else:
            data = "{}"
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return {"code": -1, "msg": 'error ' + str(e)}
    finally:
        cur.close()
    return {"code": 0, "msg": "ok", "data": data}


def get_list(table, page_num=1, page_size=20, fields: str | list = '*', conditions=None) -> dict:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        total_count = cur.fetchone()[0]
        if type(fields) == 'str':
            field_str = fields
        else:
            field_str = ','.join(fields)
        condition_str = ''
        if conditions and type(conditions) == dict:
            for k, v in conditions.items():
                condition_str += f" AND {k}='{v}'"
        sql_str = f"""SELECT {field_str} FROM {table} WHERE 1=1 {condition_str} ORDER BY id DESC LIMIT ? OFFSET ?;"""
        log.info(sql_str)
        cur.execute(sql_str, (page_size, (page_num - 1) * page_size))

        result = cur.fetchall()
        data = {
            'data': [dict(zip([col[0] for col in cur.description], row)) for row in result],
            'totalCount': total_count,
            'pageNum': page_num,
            'pageSize': page_size,
            'totalPage': (total_count + page_size - 1) // page_size,
        }
    except Exception as e:
        log.error(e)
        traceback.print_exc()
        return {"code": -1, "msg": 'error ' + str(e)}
    finally:
        cur.close()
    return {"code": 0, "msg": "ok", "data": data}
