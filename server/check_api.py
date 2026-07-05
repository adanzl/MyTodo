import json, urllib.request
url = "http://127.0.0.1:8000/api/todo/calendar?startTime=2026-07-05&endTime=2026-07-11&userId=3"
data = json.loads(urllib.request.urlopen(url).read())
found = False
for date, schedules in data["data"].items():
    for s in schedules:
        if s["title"] == "测试" and s["id"] == 329:
            print(f"找到! [{date}] id={s['id']} title={s['title']} startTs={s['startTs']} userId={s.get('userId')}")
            found = True
if not found:
    print("没找到 id=329 的测试日程")
    print("7月5日的日程:", [f"{s['id']}:{s['title']}" for s in data["data"].get("2026-07-05", [])])
