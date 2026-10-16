"""文字提取支持的站点。

新增网站时在这里登记显示名和域名。下载仍统一走 yt-dlp，页面不用改结构。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


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
