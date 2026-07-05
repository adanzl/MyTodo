import sqlite3
c = sqlite3.connect("data.db")
cur = c.cursor()
cur.execute("UPDATE t_schedule SET user_id=3 WHERE user_id IS NULL")
print("updated:", cur.rowcount)
c.commit()
cur.execute("SELECT id, title, user_id FROM t_schedule WHERE id=329")
print(cur.fetchone())
c.close()
