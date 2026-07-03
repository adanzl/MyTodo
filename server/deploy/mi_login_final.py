"""
在服务器直接运行: /home/leo/.conda/envs/flask_env/bin/python /tmp/mi_login_final.py
会自动填写账号密码，遇到短信验证码时让你输入，最后保存 token 到 ~/.mi.token
"""
import asyncio, json, os
from playwright.async_api import async_playwright

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
MI_USER = os.getenv("MI_USER", "")
MI_PASS = os.getenv("MI_PASS", "")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path="/home/leo/.conda/envs/flask_env/lib/python3.13/site-packages/playwright/browsers/chromium-1228/chrome-linux/chrome",
            args=["--no-sandbox", "--disable-setuid-sandbox", "--headless=new"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        login_data = {}

        async def on_response(response):
            url = str(response.url)
            if "sts" in url or "serviceLoginAuth2" in url:
                try:
                    body = await response.text()
                    if body.startswith("&&&START&&&"):
                        d = json.loads(body[11:])
                        if "userId" in d:
                            login_data.update(d)
                except:
                    pass
        page.on("response", on_response)

        print("[1/6] 获取登录页...")
        await page.goto("https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true")
        body = await page.text_content("body") or ""
        data = json.loads(body[11:])
        await page.goto(data["location"])
        await page.wait_for_timeout(3000)

        print("[2/6] 接受 cookie...")
        try:
            btn = page.locator('button:has-text("Accept")')
            if await btn.is_visible(timeout=2000):
                await btn.click()
                await page.wait_for_timeout(1000)
        except:
            pass

        print("[3/6] 勾选协议、填写账号密码...")
        await page.locator('input[type="checkbox"]').check()
        await page.fill('input[name="account"]', MI_USER)
        await page.fill('input[name="password"]', MI_PASS)

        print("[4/6] 提交登录...")
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(8000)

        # 短信验证
        if "verifyPhone" in page.url or "验证" in (await page.text_content("body") or ""):
            print("[5/6] 需要短信验证，已发送验证码到手机...")
            await page.click('button:has-text("Send")')
            await page.wait_for_timeout(2000)
            code = input("请输入手机收到的验证码: ")
            await page.locator('input[type="text"]').first.fill(code)
            await page.wait_for_timeout(500)
            try:
                await page.click('button:has-text("Verify")')
            except:
                await page.click('button[type="submit"]')
            print("验证码已提交，等待验证...")
            await page.wait_for_timeout(10000)

        print(f"[6/6] 最终 URL: {page.url}")
        cookies = await context.cookies()
        cookie_dict = {c["name"]: c["value"] for c in cookies}
        uid = cookie_dict.get("userId") or login_data.get("userId")
        pt = cookie_dict.get("passToken") or login_data.get("passToken")

        if uid:
            token = {"userId": uid, "deviceId": "ABCDEF1234567890", "passToken": pt or ""}
            with open(os.path.expanduser("~/.mi.token"), "w") as f:
                json.dump(token, f, indent=2)
            print(f"\n登录成功！userId: {uid}, token 已保存到 ~/.mi.token")
        else:
            print(f"\n登录失败！cookies: {list(cookie_dict.keys())}")

        await browser.close()

asyncio.run(main())
