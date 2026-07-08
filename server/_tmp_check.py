import sqlite3
import json
import sys
from datetime import datetime

conn = sqlite3.connect('/mnt/data/project/MyTodo/server/data.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

today = datetime.now().strftime('%Y-%m-%d')
print(f"=== Today: {today}, User: 4 ===\n")

cur.execute("""
    SELECT id, name, status, priority, type, user_id, start_date, end_date, duration, 
           pre_todo, pre_task, block_time, data 
    FROM t_task 
    WHERE user_id LIKE '%4%' 
    AND start_date <= ? 
    AND end_date >= ?
""", (today, today))

all_tasks = [dict(r) for r in cur.fetchall()]
print(f"Total tasks for user 4: {len(all_tasks)}")
for t in all_tasks:
    print(f"  - ID={t['id']}, name={t['name']}, priority={t['priority']}")

sys.path.insert(0, '/mnt/data/project/MyTodo/server')
from core.services.task.task_mgr import TaskMgr
from flask import Flask

app = Flask(__name__)
with app.app_context():
    mgr = TaskMgr()
    tasks = mgr.check_task_lock(all_tasks, user_id=4, date_str=today)
    
    print(f"\n=== Lock Status ===")
    for task in tasks:
        print(f"\nTask ID={task['id']}: {task['name']}")
        print(f"  Priority: {task.get('priority')}")
        print(f"  Lock: {task.get('lock')}")
        print(f"  Msg: {task.get('msg')}")

conn.close()
