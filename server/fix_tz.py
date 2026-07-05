"""修复数据库历史数据：UTC(Z) 时间戳 → UTC+8 带时区偏移格式"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "mytodo.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 查待修复数量
cur.execute("SELECT COUNT(*) FROM t_schedule WHERE start_ts LIKE '%Z'")
count = cur.fetchone()[0]
print(f"待修复: {count} 条")

if count > 0:
    cur.execute("""UPDATE t_schedule 
        SET start_ts = strftime('%Y-%m-%dT%H:%M:%S+08:00', start_ts, '+8 hours'),
            end_ts   = strftime('%Y-%m-%dT%H:%M:%S+08:00', end_ts, '+8 hours')
        WHERE start_ts LIKE '%Z'""")
    print(f"start_ts/end_ts 修复: {cur.rowcount} 条")

    cur.execute("""UPDATE t_schedule 
        SET repeat_end_ts = strftime('%Y-%m-%dT%H:%M:%S+08:00', repeat_end_ts, '+8 hours')
        WHERE repeat_end_ts LIKE '%Z'""")
    print(f"repeat_end_ts 修复: {cur.rowcount} 条")

conn.commit()
conn.close()
print("完成")
