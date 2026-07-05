import sqlite3
c = sqlite3.connect("data.db")
c.row_factory = sqlite3.Row
r = c.execute("SELECT id,title,start_ts,user_id,repeat FROM t_schedule WHERE id=329").fetchone()
print(dict(r))
c.close()
