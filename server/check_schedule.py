import sqlite3
c = sqlite3.connect("data.db")
c.row_factory = sqlite3.Row
r = c.execute("SELECT * FROM t_schedule WHERE id=329").fetchall()
for k in r[0].keys():
    print(k, "=", repr(r[0][k]))
c.close()
