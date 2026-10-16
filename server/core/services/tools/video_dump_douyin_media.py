"""用浏览器打开抖音视频页，拿到页面自己请求到的播放地址再下载。

yt-dlp 的抖音提取器只请求没有签名的 aweme/detail，站点会拒绝，并报
Fresh cookies are needed。登录态也补不上这个签名。视频页在浏览器里会自己
带签名请求详情，这里只收下那个结果。
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
from typing import Optional
from urllib.parse import urlparse

import requests

_PAGE_TIMEOUT_MS = 25_000
_WAIT_SECONDS = 20.0
_MIN_BYTES = 8_192
# 只做下载请求的兜底 UA。不要拿它覆盖浏览器 UA：UA 和真实浏览器对不上时，
# 抖音会给详情接口回空包（bdturing 风控），这里就取不到播放地址。
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def _sites():
    """按文件加载站点规则，避免 python 直接跑这个脚本时把整个服务导入进来。"""
    name = "video_dump_sites_standalone"
    loaded = sys.modules.get(name)
    if loaded is not None:
        return loaded
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_dump_sites.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _browser_module():
    """同样按文件加载：这个脚本会被 python 直接执行，没有包上下文。"""
    name = "video_dump_douyin_browser_standalone"
    loaded = sys.modules.get(name)
    if loaded is not None:
        return loaded
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_dump_douyin_browser.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def open_url(url: str) -> str:
    """只接受抖音的 https 链接。笔记页会先收成 /video/{id}。"""
    sites = _sites()
    raw = sites.canonical_url((url or "").strip())
    site = sites.match_site(raw)
    if not site or site.id != "douyin":
        return ""
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        return ""
    return raw


def play_urls(detail: dict) -> list[str]:
    """优先 h264 的 mp4，清晰度从高到低。跳过 h265 和 dash。"""
    video = detail.get("video") if isinstance(detail, dict) else None
    if not isinstance(video, dict):
        return []
    ranked: list[tuple[int, str]] = []
    for item in video.get("bit_rate") or []:
        if not isinstance(item, dict):
            continue
        if item.get("is_h265"):
            continue
        if str(item.get("format") or "") != "mp4":
            continue
        address = _first_url((item.get("play_addr") or {}).get("url_list"))
        if not address:
            continue
        try:
            quality = int(item.get("quality_type") or 999)
        except (TypeError, ValueError):
            quality = 999
        ranked.append((quality, address))
    ranked.sort(key=lambda pair: pair[0])
    found: list[str] = []
    seen: set[str] = set()
    for _quality, address in ranked:
        if address in seen:
            continue
        seen.add(address)
        found.append(address)
    for key in ("play_addr_h264", "play_addr", "download_addr"):
        address = _first_url((video.get(key) or {}).get("url_list"))
        if address and address not in seen:
            seen.add(address)
            found.append(address)
    return found


def media_title(detail: dict) -> str:
    if not isinstance(detail, dict):
        return ""
    return str(detail.get("desc") or detail.get("aweme_id") or "").strip()


def is_note(detail: dict) -> bool:
    """图文笔记。带 images 的帖子没有能下载的视频：它的 play_addr 指向图片桶，取回来是 404。"""
    if not isinstance(detail, dict):
        return False
    images = detail.get("images")
    return isinstance(images, list) and len(images) > 0


def netscape_cookies(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in (text or "").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _flag, path, secure, expires, name, value = parts[:7]
        if "douyin.com" not in domain or not name:
            continue
        if any(ch in value for ch in "\r\n"):
            continue
        item = {
            "name": name,
            "value": value,
            "domain": domain,
            "path": path or "/",
            "secure": secure.upper() == "TRUE",
        }
        try:
            exp = int(expires)
        except ValueError:
            exp = 0
        if exp > 0:
            item["expires"] = exp
        rows.append(item)
    return rows


def run(page_url: str, dest: str, result_path: str, cookie_file: str = "") -> None:
    target = open_url(page_url)
    if not target:
        _write_result(result_path, ok=False, error="不是抖音视频链接")
        return
    try:
        title = _fetch(target, dest, cookie_file)
    except Exception as exc:
        _write_result(result_path, ok=False, error=_public_error(exc))
        return
    _write_result(result_path, ok=True, title=title)


def _fetch(page_url: str, dest: str, cookie_file: str) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("no-playwright") from exc

    holder: dict = {}
    with sync_playwright() as playwright:
        try:
            browser = _browser_module().launch_browser(playwright)
        except Exception as exc:
            raise RuntimeError("no-browser") from exc
        context = browser.new_context(locale="zh-CN")
        saved = _read_cookie_file(cookie_file)
        if saved:
            try:
                context.add_cookies(saved)
            except Exception:
                pass
        page = context.new_page()
        page.on("response", lambda response: _capture_detail(holder, response))
        page.goto(page_url, wait_until="domcontentloaded", timeout=_PAGE_TIMEOUT_MS)
        deadline = time.monotonic() + _WAIT_SECONDS
        while not holder.get("detail") and time.monotonic() < deadline:
            page.wait_for_timeout(500)
        detail = holder.get("detail")
        if not isinstance(detail, dict):
            browser.close()
            raise RuntimeError("no-detail")
        if is_note(detail):
            browser.close()
            raise RuntimeError("note")
        urls = play_urls(detail)
        if not urls:
            browser.close()
            raise RuntimeError("no-play")
        title = media_title(detail)
        agent = page.evaluate("() => navigator.userAgent") or _UA
        last_error = "download"
        for address in urls[:4]:
            try:
                _save_media(context, address, dest, str(agent))
                last_error = ""
                break
            except Exception:
                last_error = "download"
        browser.close()
        if last_error:
            raise RuntimeError(last_error)
        return title


def _capture_detail(holder: dict, response) -> None:
    if holder.get("detail"):
        return
    if "aweme/v1/web/aweme/detail/" not in (response.url or ""):
        return
    if response.status != 200:
        return
    try:
        payload = response.json()
    except Exception:
        return
    detail = payload.get("aweme_detail") if isinstance(payload, dict) else None
    if isinstance(detail, dict) and detail.get("aweme_id"):
        holder["detail"] = detail


def _save_media(context, address: str, dest: str, user_agent: str) -> None:
    session = requests.Session()
    for row in context.cookies():
        session.cookies.set(
            row["name"],
            row["value"],
            domain=row.get("domain") or None,
            path=row.get("path") or "/",
        )
    directory = os.path.dirname(dest)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory or None, prefix=".media-", suffix=".part")
    os.close(fd)
    try:
        with session.get(
            address,
            headers={"User-Agent": user_agent, "Referer": "https://www.douyin.com/"},
            stream=True,
            timeout=(10, 60),
        ) as resp:
            resp.raise_for_status()
            if "text/html" in (resp.headers.get("content-type") or ""):
                raise RuntimeError("html")
            size = 0
            header = b""
            with open(tmp, "wb") as handle:
                for chunk in resp.iter_content(256 * 1024):
                    if not chunk:
                        continue
                    if len(header) < 32:
                        header += chunk
                    handle.write(chunk)
                    size += len(chunk)
                    if len(header) >= 12 and b"ftyp" not in header[:32]:
                        raise RuntimeError("not-mp4")
        if size < _MIN_BYTES or b"ftyp" not in header[:32]:
            raise RuntimeError("small")
        os.replace(tmp, dest)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _read_cookie_file(path: str) -> list[dict]:
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return netscape_cookies(handle.read())
    except OSError:
        return []


def _first_url(values) -> str:
    if not isinstance(values, list):
        return ""
    for item in values:
        text = str(item or "").strip()
        if text.startswith("https://"):
            return text
    return ""


def _public_error(exc: Exception) -> str:
    text = str(exc)
    if "Executable doesn't exist" in text or "executable" in text.lower() or text == "no-browser":
        return "服务器没找到可用的浏览器，暂时无法下载抖音视频（可用 VIDEO_DUMP_CHROME_PATH 指定 Chrome）"
    if text == "no-playwright":
        return "服务器还没安装浏览器组件，暂时无法下载抖音视频"
    if text == "note":
        return "这是图文笔记，没有可下载的视频"
    if text in {"no-detail", "no-play"}:
        return "抖音没有返回视频地址，请稍后重试"
    return "视频文件下载失败"


def _write_result(path: str, ok: bool, title: str = "", error: str = "") -> None:
    payload = {"ok": ok, "title": title, "error": error}
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory or None, prefix=".fetch-", suffix=".tmp")
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


def main(argv: Optional[list[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) not in (3, 4):
        return 2
    page_url, dest, result_path = args[:3]
    cookie_file = args[3] if len(args) == 4 else ""
    run(page_url, dest, result_path, cookie_file)
    try:
        with open(result_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return 1
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
