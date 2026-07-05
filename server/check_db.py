naimport sqlite3, os
base = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base, "data", "mytodo.db")
c = sqlite3.connect(db_path)
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("Tables:", tables)
c.close()
