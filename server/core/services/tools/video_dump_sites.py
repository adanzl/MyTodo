"""文字提取支持的站点。

新增网站时在这里登记显示名和域名。下载仍统一走 yt-dlp，页面不用改结构。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_URL_TRAILING = "，。、,.;:!?）)】」』\"'"
# yt-dlp 的 Douyin 提取器只匹配 douyin.com/video/{数字}。笔记和分享页用的是同一个作品 id。
_DOUYIN_CONTENT_RE = re.compile(
    r"^https?://(?:[\w.-]+\.)?(?:douyin\.com|iesdouyin\.com)/(?:share/)?(?P<kind>note|video|gallery)/(?P<id>\d+)",
    re.IGNORECASE,
)
_DOUYIN_MODAL_RE = re.compile(
    r"^https?://(?:[\w.-]+\.)?douyin\.com/(?!video/)[^\s]*?[?&]modal_id=(?P<id>\d+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class VideoSite:
    id: str
    label: str
    hosts: tuple[str, ...]


SITES: tuple[VideoSite, ...] = (
    VideoSite("bilibili", "哔哩哔哩", ("bilibili.com", "b23.tv")),
    VideoSite("douyin", "抖音", ("douyin.com", "iesdouyin.com")),
)


def list_sites() -> list[dict]:
    return [{"id": site.id, "label": site.label, "hosts": list(site.hosts)} for site in SITES]


def extract_url(text: str) -> str:
    """从分享文案里取出第一个 http(s) 链接。已经是纯链接时原样返回。"""
    match = _URL_RE.search(text or "")
    if not match:
        return ""
    return canonical_url(match.group(0).rstrip(_URL_TRAILING))


def canonical_url(url: str) -> str:
    """把抖音笔记、分享页改成 yt-dlp 能识别的 /video/{id}。其它链接原样返回。"""
    raw = (url or "").strip()
    match = _DOUYIN_CONTENT_RE.match(raw)
    if match and _douyin_needs_video_form(raw, match.group("kind")):
        return f"https://www.douyin.com/video/{match.group('id')}"
    modal = _DOUYIN_MODAL_RE.match(raw)
    if modal:
        return f"https://www.douyin.com/video/{modal.group('id')}"
    return raw


def _douyin_needs_video_form(url: str, kind: str) -> bool:
    if kind.lower() != "video":
        return True
    if "/share/" in urlparse(url).path.lower():
        return True
    return site_host(url) != "douyin.com"


def site_host(url: str) -> str:
    host = (urlparse((url or "").strip()).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def match_site(url: str) -> Optional[VideoSite]:
    host = site_host(url)
    if not host:
        return None
    for site in SITES:
        for item in site.hosts:
            if host == item or host.endswith("." + item):
                return site
    return None
