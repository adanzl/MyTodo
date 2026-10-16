"""文字提取的站点登录态。

页面负责展示二维码，这里向站点申请二维码、轮询扫码结果，并把 Set-Cookie 交给 yt-dlp。
两个站点都是手机 App 扫码，不读用户名密码，也不要求用户复制 Cookie。
抖音的申请接口要浏览器签名，所以二维码由本机浏览器打开登录页后取回。

登录态写成 Netscape cookies.txt，按站点分文件。下载时优先用页面保存的文件，
没有再用环境变量 VIDEO_DUMP_COOKIES_FILE。
"""
from __future__ import annotations

import os
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from core.config import VIDEO_DUMP_BASE_DIR, app_logger, config
from core.services.tools.video_dump_douyin_browser import (
    LOGIN_COOKIE_NAMES,
    qr_image,
    qr_path,
    read_json,
    safe_douyin_url,
    save_cookie_rows,
    stop_path,
)
from core.services.tools.video_dump_sites import match_site

log = app_logger

_BILIBILI_QR_GENERATE = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
_BILIBILI_QR_POLL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
_DOUYIN_QR_WAIT = 20.0
_WORKER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_dump_douyin_browser.py")
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
# 建连要短，读也封顶：passport 不回包时不能把 hub 挂住。
_TIMEOUT = (5, 10)
_QR_TTL = 180.0
# 未登录时也可能有 ttwid。这些名字才表示已经登录。
_DOUYIN_LOGIN_KEYS = LOGIN_COOKIE_NAMES

_POLL_STATUS = {
    86101: "waiting",
    86090: "scanned",
    86038: "expired",
    0: "success",
}

_SITES = (
    {"id": "bilibili", "label": "哔哩哔哩", "method": "qr"},
    {"id": "douyin", "label": "抖音", "method": "qr"},
)


@dataclass
class _QrLogin:
    site: str
    session: requests.Session
    key: str
    created: float
    params: dict = field(default_factory=dict)


@dataclass
class _DouyinJob:
    directory: str
    created: float


_lock = threading.Lock()
_qr_logins: dict[str, _QrLogin] = {}
_douyin_jobs: dict[str, _DouyinJob] = {}


def _cookie_dir() -> str:
    return os.path.join(VIDEO_DUMP_BASE_DIR, "cookies")


def cookie_path(site_id: str) -> str:
    if site_id not in {item["id"] for item in _SITES}:
        raise ValueError(f"unknown site: {site_id}")
    return os.path.join(_cookie_dir(), f"{site_id}.txt")


def list_login_status() -> list[dict]:
    return [{**item, "ready": site_ready(item["id"])} for item in _SITES]


def site_ready(site_id: str) -> bool:
    path = cookie_path(site_id)
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read(8000)
    except OSError:
        return False
    if site_id == "bilibili":
        return "\tSESSDATA\t" in text
    if site_id == "douyin":
        return ".douyin.com" in text and any(f"\t{name}\t" in text for name in _DOUYIN_LOGIN_KEYS)
    return False


def cookies_file_for_url(url: str) -> str:
    """下载这个链接时要用的 cookies 文件。没有则返回空字符串。"""
    site = match_site(url)
    if site and site.id in {item["id"] for item in _SITES}:
        path = cookie_path(site.id)
        if os.path.isfile(path):
            return path
    env_path = (config.VIDEO_DUMP_COOKIES_FILE or "").strip()
    if env_path and os.path.isfile(env_path):
        return env_path
    return ""


def start_bilibili_qr() -> tuple[int, str, Optional[dict]]:
    session = requests.Session()
    session.headers["User-Agent"] = _UA
    session.headers["Referer"] = "https://www.bilibili.com/"
    try:
        response = session.get(_BILIBILI_QR_GENERATE, timeout=_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        log.warning("[文字提取] 申请 B 站二维码失败: %s", type(exc).__name__)
        return -1, "申请二维码失败，请稍后重试", None
    if not isinstance(payload, dict) or payload.get("code") != 0:
        return -1, "哔哩哔哩没有返回二维码", None
    data = payload.get("data") or {}
    url = str(data.get("url") or "").strip()
    qrcode_key = str(data.get("qrcode_key") or "").strip()
    if not url.startswith("https://") or not qrcode_key:
        return -1, "哔哩哔哩没有返回二维码", None
    login_id = secrets.token_hex(16)
    with _lock:
        _purge_locked()
        _qr_logins[login_id] = _QrLogin(
            site="bilibili", session=session, key=qrcode_key, created=time.monotonic(),
        )
    return 0, "ok", {"login_id": login_id, "url": url}


def poll_bilibili_qr(login_id: str) -> tuple[int, str, Optional[dict]]:
    login_id = (login_id or "").strip()
    with _lock:
        item = _qr_logins.get(login_id)
        if item is None or item.site != "bilibili" or time.monotonic() - item.created > _QR_TTL:
            if item is not None and item.site == "bilibili":
                _qr_logins.pop(login_id, None)
            return 0, "ok", {"status": "expired", "ready": site_ready("bilibili")}
        session = item.session
        qrcode_key = item.key
    try:
        response = session.get(_BILIBILI_QR_POLL, params={"qrcode_key": qrcode_key}, timeout=_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        log.warning("[文字提取] 查询 B 站扫码状态失败: %s", type(exc).__name__)
        return -1, "查询扫码状态失败，请稍后重试", None
    data = payload.get("data") if isinstance(payload, dict) else None
    code = data.get("code") if isinstance(data, dict) else None
    status = _POLL_STATUS.get(code)
    if status == "success":
        saved = _save_bilibili_jar(session.cookies)
        with _lock:
            _qr_logins.pop(login_id, None)
        if not saved:
            return -1, "扫码成功但没有拿到登录态，请重试", None
        return 0, "ok", {"status": "success", "ready": True}
    if status in {"waiting", "scanned"}:
        return 0, "ok", {"status": status, "ready": False}
    with _lock:
        _qr_logins.pop(login_id, None)
    return 0, "ok", {"status": "expired", "ready": site_ready("bilibili")}


def start_douyin_qr() -> tuple[int, str, Optional[dict]]:
    """用本机浏览器打开抖音登录页，返回二维码图片。不返回 token。"""
    login_id = secrets.token_hex(16)
    job_dir = os.path.join(_cookie_dir(), "douyin-qr", login_id)
    os.makedirs(job_dir, exist_ok=True)
    with _lock:
        _purge_locked()
        _douyin_jobs[login_id] = _DouyinJob(directory=job_dir, created=time.monotonic())
    try:
        _spawn_douyin_worker(job_dir)
    except Exception as exc:
        log.warning("[文字提取] 启动抖音登录页失败: %s", type(exc).__name__)
        _stop_douyin_job(login_id)
        return -1, "申请二维码失败，请稍后重试", None
    image, url = _wait_douyin_qr(job_dir, _DOUYIN_QR_WAIT)
    if not image and not url:
        message = str(read_json(os.path.join(job_dir, "state.json")).get("message") or "")
        _stop_douyin_job(login_id)
        return -1, message or "申请二维码失败，请稍后重试", None
    result = {"login_id": login_id}
    if image:
        result["image"] = image
    if url:
        result["url"] = url
    return 0, "ok", result


def poll_douyin_qr(login_id: str) -> tuple[int, str, Optional[dict]]:
    login_id = (login_id or "").strip()
    with _lock:
        job = _douyin_jobs.get(login_id)
        if job is None or time.monotonic() - job.created > _QR_TTL:
            if job is not None:
                _douyin_jobs.pop(login_id, None)
                _touch_stop(job.directory)
            return 0, "ok", {"status": "expired", "ready": site_ready("douyin")}
        job_dir = job.directory
    state = read_json(os.path.join(job_dir, "state.json"))
    status = str(state.get("status") or "waiting")
    if status == "error":
        _stop_douyin_job(login_id)
        return -1, str(state.get("message") or "查询扫码状态失败，请稍后重试"), None
    if status == "saved":
        _stop_douyin_job(login_id)
        if not site_ready("douyin"):
            return -1, "扫码成功但没有拿到登录态，请重试", None
        return 0, "ok", {"status": "success", "ready": True}
    if status == "expired":
        _stop_douyin_job(login_id)
        return 0, "ok", {"status": "expired", "ready": site_ready("douyin")}
    if status in {"scanned", "success"}:
        return 0, "ok", {"status": "scanned", "ready": False}
    return 0, "ok", {"status": "waiting", "ready": False}


def logout(site_id: str) -> tuple[int, str]:
    if site_id not in {item["id"] for item in _SITES}:
        return -1, "未知站点"
    path = cookie_path(site_id)
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError as exc:
        log.warning("[文字提取] 清除登录态失败: %s", type(exc).__name__)
        return -1, "清除登录态失败"
    return 0, "已退出"


def _spawn_douyin_worker(job_dir: str) -> None:
    """子进程跑浏览器。

    main.py 里 patch_all(subprocess=True) 之后只能用 gevent 版的 Popen：
    get_original 拿回来的是打补丁前的类，而它依赖的 subprocess._fork_exec
    已被 gevent 置成 None，一调用就抛 TypeError。
    子进程交给 hub 的 child watcher 回收，不用自己 wait。
    """
    kwargs = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x08000000
    subprocess.Popen(
        [sys.executable, _WORKER_SCRIPT, job_dir, cookie_path("douyin")],
        **kwargs,
    )


def _wait_douyin_qr(job_dir: str, timeout: float) -> tuple[str, str]:
    from gevent import sleep as hub_sleep

    deadline = time.monotonic() + timeout
    while True:
        image, url = _read_douyin_qr(job_dir)
        if image or url:
            return image, url
        state = read_json(os.path.join(job_dir, "state.json"))
        if str(state.get("status") or "") == "error":
            return "", ""
        if time.monotonic() >= deadline:
            return "", ""
        hub_sleep(0.2)


def _read_douyin_qr(job_dir: str) -> tuple[str, str]:
    payload = read_json(qr_path(job_dir))
    image = qr_image(str(payload.get("image") or ""))
    url = str(payload.get("url") or "").strip()
    if not safe_douyin_url(url):
        url = ""
    return image, url


def _stop_douyin_job(login_id: str) -> None:
    with _lock:
        job = _douyin_jobs.pop(login_id, None)
    if job is not None:
        _touch_stop(job.directory)


def _touch_stop(directory: str) -> None:
    try:
        with open(stop_path(directory), "a", encoding="utf-8"):
            pass
    except OSError as exc:
        log.info("[文字提取] 结束抖音登录页未成功: %s", type(exc).__name__)


def _save_douyin_cookie_rows(rows: list[dict]) -> bool:
    return save_cookie_rows(cookie_path("douyin"), rows)


def _save_bilibili_jar(jar: requests.cookies.RequestsCookieJar) -> bool:
    lines = ["# Netscape HTTP Cookie File", ""]
    found = False
    for cookie in jar:
        domain = cookie.domain or ""
        name = cookie.name or ""
        value = cookie.value or ""
        if "bilibili.com" not in domain or not name:
            continue
        if any(ch in value for ch in "\r\n\t"):
            continue
        lines.append(_netscape_row(domain, cookie.path or "/", bool(cookie.secure), int(cookie.expires or 0), name, value))
        if name == "SESSDATA":
            found = True
    if not found:
        return False
    _atomic_write(cookie_path("bilibili"), "\n".join(lines) + "\n")
    return True


def _netscape_row(domain: str, path: str, secure: bool, expires: int, name: str, value: str) -> str:
    include_sub = "TRUE" if domain.startswith(".") else "FALSE"
    return "\t".join([
        domain,
        include_sub,
        path or "/",
        "TRUE" if secure else "FALSE",
        str(int(expires)),
        name,
        value,
    ])


def _atomic_write(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".cookie-", suffix=".tmp")
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


def _purge_locked() -> None:
    now = time.monotonic()
    expired = [key for key, item in _qr_logins.items() if now - item.created > _QR_TTL]
    for key in expired:
        _qr_logins.pop(key, None)
    expired_jobs = [key for key, job in _douyin_jobs.items() if now - job.created > _QR_TTL]
    for key in expired_jobs:
        job = _douyin_jobs.pop(key)
        _touch_stop(job.directory)
