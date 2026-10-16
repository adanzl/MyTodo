"""文字提取的站点登录态。

页面负责展示二维码，这里向站点申请二维码、轮询扫码结果，并把 Set-Cookie 交给 yt-dlp。
两个站点都是手机 App 扫码，不读用户名密码，也不要求用户复制 Cookie。

登录态写成 Netscape cookies.txt，按站点分文件。下载时优先用页面保存的文件，
没有再用环境变量 VIDEO_DUMP_COOKIES_FILE。
"""
from __future__ import annotations

import os
import re
import secrets
import string
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests

from core.config import VIDEO_DUMP_BASE_DIR, app_logger, config
from core.services.tools.video_dump_sites import match_site

log = app_logger

_BILIBILI_QR_GENERATE = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
_BILIBILI_QR_POLL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
_DOUYIN_QR_GENERATE = "https://sso.douyin.com/get_qrcode/"
_DOUYIN_QR_POLL = "https://sso.douyin.com/check_qrconnect/"
_DOUYIN_HOME = "https://www.douyin.com/"
_DOUYIN_REDIRECT_HOSTS = (
    "douyin.com",
    "iesdouyin.com",
    "douyin.cn",
    "snssdk.com",
    "amemv.com",
    "bytedance.com",
)
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
# 建连要短，读也封顶：passport 不回包时不能把 hub 挂住。
_TIMEOUT = (5, 10)
_QR_TTL = 180.0
# 未登录时也可能有 ttwid。这些名字才表示已经登录。
_DOUYIN_LOGIN_KEYS = frozenset({
    "sessionid",
    "sessionid_ss",
    "sid_guard",
    "sid_tt",
    "uid_tt",
    "uid_tt_ss",
})

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


_lock = threading.Lock()
_qr_logins: dict[str, _QrLogin] = {}


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
    """申请一张抖音登录二维码。返回图片或可编码的 https 链接，不返回 token。"""
    fp = _verify_fp()
    params = {
        "service": _DOUYIN_HOME.rstrip("/"),
        "need_logo": "false",
        "need_short_url": "false",
        "device_platform": "web_app",
        "aid": "6383",
        "account_sdk_source": "sso",
        "sdk_version": "2.2.5",
        "language": "zh",
        "verifyFp": fp,
        "fp": fp,
    }
    session = requests.Session()
    session.headers["User-Agent"] = _UA
    session.headers["Referer"] = _DOUYIN_HOME
    session.cookies.set("s_v_web_id", fp, domain=".douyin.com", path="/")
    try:
        session.get(_DOUYIN_HOME, timeout=_TIMEOUT)
    except Exception as exc:
        log.info("[文字提取] 访问抖音主站未成功，继续申请二维码: %s", type(exc).__name__)
    try:
        response = session.get(_DOUYIN_QR_GENERATE, params=params, timeout=_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        log.warning("[文字提取] 申请抖音二维码失败: %s", type(exc).__name__)
        return -1, "申请二维码失败，请稍后重试", None
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return -1, "抖音没有返回二维码", None
    token = str(data.get("token") or "").strip()
    image = _qr_image(str(data.get("qrcode") or ""))
    url = str(data.get("qrcode_index_url") or data.get("frontend_show_qrcode") or "").strip()
    if not _safe_douyin_url(url):
        url = ""
    if not token or (not image and not url):
        return -1, "抖音没有返回二维码", None
    login_id = secrets.token_hex(16)
    with _lock:
        _purge_locked()
        _qr_logins[login_id] = _QrLogin(
            site="douyin", session=session, key=token, created=time.monotonic(), params=params,
        )
    result = {"login_id": login_id}
    if image:
        result["image"] = image
    if url.startswith("https://"):
        result["url"] = url
    return 0, "ok", result


def poll_douyin_qr(login_id: str) -> tuple[int, str, Optional[dict]]:
    login_id = (login_id or "").strip()
    with _lock:
        item = _qr_logins.get(login_id)
        if item is None or item.site != "douyin" or time.monotonic() - item.created > _QR_TTL:
            if item is not None and item.site == "douyin":
                _qr_logins.pop(login_id, None)
            return 0, "ok", {"status": "expired", "ready": site_ready("douyin")}
        session = item.session
        params = dict(item.params)
        params["token"] = item.key
    try:
        response = session.get(_DOUYIN_QR_POLL, params=params, timeout=_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        log.warning("[文字提取] 查询抖音扫码状态失败: %s", type(exc).__name__)
        return -1, "查询扫码状态失败，请稍后重试", None
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return 0, "ok", {"status": "waiting", "ready": False}
    code = str(data.get("status", ""))
    redirect_url = str(data.get("redirect_url") or "").strip()
    if code in {"3", "4"} or redirect_url:
        saved = _finalize_douyin(session, redirect_url)
        with _lock:
            _qr_logins.pop(login_id, None)
        if not saved:
            return -1, "扫码成功但没有拿到登录态，请重试", None
        return 0, "ok", {"status": "success", "ready": True}
    if code == "2":
        return 0, "ok", {"status": "scanned", "ready": False}
    if code == "5":
        with _lock:
            _qr_logins.pop(login_id, None)
        return 0, "ok", {"status": "expired", "ready": site_ready("douyin")}
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


def _finalize_douyin(session: requests.Session, redirect_url: str) -> bool:
    if redirect_url:
        _follow_safe(session, redirect_url)
    try:
        session.get(_DOUYIN_HOME, timeout=_TIMEOUT, allow_redirects=False)
    except Exception as exc:
        log.info("[文字提取] 扫码后访问抖音主站未成功: %s", type(exc).__name__)
    return _save_douyin_jar(session.cookies)


def _follow_safe(session: requests.Session, url: str) -> None:
    current = url
    for _ in range(5):
        if not _safe_douyin_url(current):
            return
        try:
            response = session.get(current, timeout=_TIMEOUT, allow_redirects=False)
        except Exception as exc:
            log.info("[文字提取] 跟随抖音登录跳转未成功: %s", type(exc).__name__)
            return
        if response.status_code not in {301, 302, 303, 307, 308}:
            return
        location = response.headers.get("Location") or ""
        if not location:
            return
        current = urljoin(current, location)


def _safe_douyin_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        return False
    return any(host == item or host.endswith("." + item) for item in _DOUYIN_REDIRECT_HOSTS)


def _verify_fp() -> str:
    alphabet = string.ascii_letters + string.digits
    number = int(time.time() * 1000)
    base36 = ""
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    while number:
        base36 = digits[number % 36] + base36
        number //= 36
    tail = "".join(secrets.choice(alphabet) for _ in range(36))
    return f"verify_{base36}_{tail}"


def _qr_image(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("data:image/") and len(text) <= 200_000:
        return text
    compact = "".join(text.split())
    if not compact or len(compact) > 200_000 or not re.fullmatch(r"[A-Za-z0-9+/=]+", compact):
        return ""
    return "data:image/png;base64," + compact


def _save_douyin_jar(jar: requests.cookies.RequestsCookieJar) -> bool:
    lines = ["# Netscape HTTP Cookie File", ""]
    found = False
    for cookie in jar:
        domain = cookie.domain or ""
        name = cookie.name or ""
        value = cookie.value or ""
        if "douyin.com" not in domain or not name:
            continue
        if any(ch in value for ch in "\r\n\t"):
            continue
        lines.append(_netscape_row(domain, cookie.path or "/", bool(cookie.secure), int(cookie.expires or 0), name, value))
        if name in _DOUYIN_LOGIN_KEYS:
            found = True
    if not found:
        return False
    _atomic_write(cookie_path("douyin"), "\n".join(lines) + "\n")
    return True


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
