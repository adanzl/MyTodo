import sqlite3
c = sqlite3.connect("data.db")
c.execute("UPDATE t_schedule SET user_id=3 WHERE user_id IS NULL")
print("updated", c.rowcount)
c.commit()
c.close()
