import json, urllib.request, sys
url = "http://127.0.0.1:8000/api/todo/calendar?startTime=2026-07-05&endTime=2026-07-11&userId=3"
data = json.loads(urllib.request.urlopen(url).read())
for date, schedules in data.get("data", {}).items():
    for s in schedules:
        if s.get("title") == "测试" or s.get("id") == 329:
            print(f"[{date}] id={s['id']} title={s['title']} startTs={s['startTs']}")
print("---")
for date, schedules in data.get("data", {}).items():
    print(f"{date}: {len(schedules)}条")
