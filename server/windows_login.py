"""
在本地 (Windows) 运行此脚本完成小米登录验证
验证后会提示从浏览器获取 cookie，构造 token 文件
"""
import json, hashlib, os
import requests
import urllib3
urllib3.disable_warnings()

from dotenv import load_dotenv
load_dotenv()
MI_USER = os.getenv("MI_USER", "")
MI_PASS = os.getenv("MI_PASS", "")
DEVICE_ID = "ABCDEF1234567890"

session = requests.Session()
session.verify = False
session.cookies.set("deviceId", DEVICE_ID)
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Step 1
r = session.get("https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true", headers=headers)
d1 = json.loads(r.text[11:])
print(f"Step1: code={d1.get('code')}")

# Step 2
data_login = {
    "_json": "true",
    "qs": d1["qs"], "sid": d1["sid"], "_sign": d1["_sign"],
    "callback": d1["callback"],
    "user": MI_USER,
    "hash": hashlib.md5(MI_PASS.encode()).hexdigest().upper(),
}
r = session.post("https://account.xiaomi.com/pass/serviceLoginAuth2", data=data_login, headers=headers)
d2 = json.loads(r.text[11:])
print(f"Step2: code={d2.get('code')}, securityStatus={d2.get('securityStatus')}")

if d2.get("securityStatus") != 0:
    notify_url = d2.get("notificationUrl", "")
    print(f"\n请在新开的浏览器页面完成验证，然后复制地址栏的最终网址粘贴到这里：")
    print(f"\n验证链接：{notify_url}\n")
    final_url = input("验证完成后，粘贴浏览器地址栏的最终网址: ").strip()

    # 尝试从回调 URL 中提取参数
    from urllib.parse import urlparse, parse_qs
    params = parse_qs(urlparse(final_url).query)
    if params:
        print(f"URL params: {list(params.keys())}")
    else:
        print("URL has no query params")

    # 使用包含认证信息的 session 重新尝试
    r = session.get(final_url, headers=headers, allow_redirects=True)
    print(f"Final: {r.url}")
    raw = r.text
    if raw.startswith("&&&START&&&"):
        d3 = json.loads(raw[11:])
        if "userId" in d3:
            d2 = d3
            print("从回调获取 token 成功")

if "userId" in d2:
    token = {
        "userId": d2["userId"],
        "deviceId": DEVICE_ID,
        "passToken": d2.get("passToken", ""),
    }
    print(f"\n登录成功！userId: {token['userId']}")
    with open("mi.token.windows", "w") as f:
        json.dump(token, f, indent=2)
    print("Token 已保存到 mi.token.windows")
else:
    print("\n自动获取失败，试试手动方式。")
    print("请在浏览器中登录 https://account.xiaomi.com")
    print("打开开发者工具(F12) -> Application -> Cookies")
    print("找到 account.xiaomi.com 的 userId 和 passToken 值，告诉我")
