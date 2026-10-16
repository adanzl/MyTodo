"""在独立进程里打开抖音登录页，取出扫码结果。

www.douyin.com/passport/web/get_qrcode 会校验浏览器签名。
不带签名时，sso 的同名地址只返回登录网页，requests 解析不到二维码。
这个进程没有 gevent，Playwright 自己启动浏览器，签名由登录页完成。
浏览器优先用 Playwright 自带的 Chromium；服务器上只有系统 Chrome 时退回用它，
不必再下载一份浏览器。
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from urllib.parse import urlparse

_LOGIN_PAGE = (
    "https://sso.douyin.com/get_qrcode/"
    "?service=https%3A%2F%2Fwww.douyin.com&need_logo=false&aid=6383"
)
_QR_PATH = "/passport/web/get_qrcode/"
_POLL_PATH = "/passport/web/check_qrconnect/"
_PAGE_TIMEOUT_MS = 20_000
_SESSION_SECONDS = 170
_COOKIE_WAIT_SECONDS = 15
# Playwright 自带的 Chromium 没下载时，退回用机器上装好的 Chrome。
_CHROME_ENV = "VIDEO_DUMP_CHROME_PATH"
_CHROME_CANDIDATES = (
    "/opt/chrome-linux/chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)
_REDIRECT_HOSTS = (
    "douyin.com",
    "iesdouyin.com",
    "douyin.cn",
    "snssdk.com",
    "amemv.com",
    "bytedance.com",
)
LOGIN_COOKIE_NAMES = frozenset({
    "sessionid",
    "sessionid_ss",
    "sid_guard",
    "sid_tt",
    "uid_tt",
    "uid_tt_ss",
})


def scan_status(data: dict) -> str:
    """把抖音 check_qrconnect 的 status 收成 waiting / scanned / success / expired。"""
    status = str(data.get("status") or "")
    if status in {"5", "expired"}:
        return "expired"
    if status in {"2", "scanned"}:
        return "scanned"
    if status in {"3", "4", "confirmed"}:
        return "success"
    return "waiting"


def read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: str, payload: dict) -> None:
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".qr-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def state_path(job_dir: str) -> str:
    return os.path.join(job_dir, "state.json")


def qr_path(job_dir: str) -> str:
    return os.path.join(job_dir, "qr.json")


def stop_path(job_dir: str) -> str:
    return os.path.join(job_dir, "stop")


def write_state(job_dir: str, status: str, message: str = "") -> None:
    write_json(state_path(job_dir), {"status": status, "message": message})


def chrome_path() -> str:
    """本机可用的 Chrome。环境变量优先，其次常见安装位置。"""
    explicit = (os.environ.get(_CHROME_ENV) or "").strip()
    if explicit and os.path.isfile(explicit):
        return explicit
    for path in _CHROME_CANDIDATES:
        if os.path.isfile(path):
            return path
    return ""


def launch_browser(playwright):
    """Playwright 自带的 Chromium 优先，没下载就退回本机 Chrome。"""
    explicit = (os.environ.get(_CHROME_ENV) or "").strip()
    if explicit and os.path.isfile(explicit):
        return playwright.chromium.launch(headless=True, executable_path=explicit)
    try:
        return playwright.chromium.launch(headless=True)
    except Exception:
        fallback = chrome_path()
        if not fallback:
            raise
        return playwright.chromium.launch(headless=True, executable_path=fallback)


def run(job_dir: str, cookie_file: str) -> None:
    """打开登录页，把二维码和扫码状态写进 job_dir。成功后把登录态写入 cookie_file。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        write_state(job_dir, "error", "服务器还没安装浏览器组件，暂时无法申请抖音二维码")
        return

    confirmed_at = 0.0
    try:
        with sync_playwright() as playwright:
            browser = launch_browser(playwright)
            context = browser.new_context(locale="zh-CN")
            page = context.new_page()
            page.on("response", lambda response: _on_response(job_dir, response))
            page.goto(_LOGIN_PAGE, wait_until="domcontentloaded", timeout=_PAGE_TIMEOUT_MS)
            deadline = time.monotonic() + _SESSION_SECONDS
            while time.monotonic() < deadline and not os.path.exists(stop_path(job_dir)):
                status = str(read_json(state_path(job_dir)).get("status") or "")
                if status == "success":
                    if confirmed_at <= 0:
                        confirmed_at = time.monotonic()
                    if save_cookie_rows(cookie_file, context.cookies()):
                        write_state(job_dir, "saved")
                        break
                    if time.monotonic() - confirmed_at > _COOKIE_WAIT_SECONDS:
                        write_state(job_dir, "error", "扫码成功但没有拿到登录态，请重试")
                        break
                elif status == "expired":
                    break
                page.wait_for_timeout(1000)
            current = str(read_json(state_path(job_dir)).get("status") or "")
            if current not in {"saved", "error", "expired"} and not os.path.exists(stop_path(job_dir)):
                write_state(job_dir, "expired")
            browser.close()
    except Exception as exc:
        write_state(job_dir, "error", _browser_error_message(exc))


def _on_response(job_dir: str, response) -> None:
    url = response.url or ""
    if _QR_PATH not in url and _POLL_PATH not in url:
        return
    if "json" not in (response.headers.get("content-type") or ""):
        return
    try:
        payload = response.json()
    except Exception:
        return
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return
    if _QR_PATH in url:
        image = qr_image(str(data.get("qrcode") or ""))
        link = str(data.get("qrcode_index_url") or "")
        if not safe_douyin_url(link):
            link = ""
        if image or link:
            write_json(qr_path(job_dir), {"image": image, "url": link})
            if str(read_json(state_path(job_dir)).get("status") or "") in {"", "starting"}:
                write_state(job_dir, "waiting")
        return
    status = scan_status(data)
    current = str(read_json(state_path(job_dir)).get("status") or "")
    if current in {"success", "saved", "error"}:
        return
    if status == "waiting" and current == "scanned":
        return
    write_state(job_dir, status)


def _browser_error_message(exc: Exception) -> str:
    text = str(exc)
    if "Executable doesn't exist" in text or "executable" in text.lower():
        return "服务器没找到可用的浏览器，暂时无法申请抖音二维码（可用 VIDEO_DUMP_CHROME_PATH 指定 Chrome）"
    return "申请二维码失败，请稍后重试"


def main() -> None:
    if len(sys.argv) != 3:
        return
    job_dir = sys.argv[1]
    cookie_file = sys.argv[2]
    if not os.path.isdir(job_dir):
        return
    run(job_dir, cookie_file)


def qr_image(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("data:image/") and len(text) <= 200_000:
        return text
    compact = "".join(text.split())
    if not compact or len(compact) > 200_000 or not re.fullmatch(r"[A-Za-z0-9+/=]+", compact):
        return ""
    mime = "image/jpeg" if compact.startswith("/9j/") else "image/png"
    return f"data:{mime};base64,{compact}"


def safe_douyin_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        return False
    return any(host == item or host.endswith("." + item) for item in _REDIRECT_HOSTS)


def save_cookie_rows(path: str, rows: list[dict]) -> bool:
    lines = ["# Netscape HTTP Cookie File", ""]
    found = False
    for row in rows:
        domain = str(row.get("domain") or "")
        name = str(row.get("name") or "")
        value = str(row.get("value") or "")
        if "douyin.com" not in domain or not name:
            continue
        if any(ch in value for ch in "\r\n\t"):
            continue
        expires = row.get("expires") or 0
        try:
            expires = int(expires)
        except (TypeError, ValueError):
            expires = 0
        if expires < 0:
            expires = 0
        lines.append("\t".join([
            domain,
            "TRUE" if domain.startswith(".") else "FALSE",
            str(row.get("path") or "/"),
            "TRUE" if row.get("secure") else "FALSE",
            str(expires),
            name,
            value,
        ]))
        if name in LOGIN_COOKIE_NAMES:
            found = True
    if not found:
        return False
    write_text(path, "\n".join(lines) + "\n")
    return True


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory or None, prefix=".cookie-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


if __name__ == "__main__":
    main()
