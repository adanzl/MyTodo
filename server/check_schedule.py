import sqlite3
c = sqlite3.connect("data.db")
r = c.execute("SELECT * FROM t_schedule WHERE id=329").fetchall()
print(r[0].keys())
for k, v in zip(r[0].keys(), r[0]):
    print(k, "=", v)
c.close()
