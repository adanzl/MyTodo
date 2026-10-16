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
    return match.group(0).rstrip(_URL_TRAILING)


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
