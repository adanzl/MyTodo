import sqlite3
c = sqlite3.connect("data.db")
r = c.execute("SELECT id, title, start_ts, repeat FROM t_schedule WHERE id=329 OR title LIKE '%测试%'").fetchall()
for row in r:
    print(row)
c.close()
