"""OpenSubtitles.com REST API 客户端。

文档: https://opensubtitles.stoplight.io/docs/opensubtitles-api/a172317bd5ccc-search-for-subtitles

``GET /api/v1/subtitles`` 常用查询参数（官方）:
  query, languages, page, order_by, order_direction, title_match,
  moviehash, filename, moviehash_match, imdb_id, tmdb_id, ...

登录后 ``base_url`` 可能无 scheme（如 ``api.opensubtitles.com``），需补全为 ``https://``。
"""

from __future__ import annotations

import os
import struct
import time
from typing import Any

import requests

from core.config import config

_READ_CHUNK = 64 * 1024
_TOKEN_TTL = 23 * 3600
_auth: dict[str, Any] = {"token": None, "expires": 0.0}


class OpenSubtitlesError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def _normalize_base_url(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if not u:
        u = "https://api.opensubtitles.com"
    elif not u.startswith(("http://", "https://")):
        u = "https://" + u.lstrip("/")
    return u


def compute_movie_hash(file_path: str) -> str:
    """OpenSubtitles moviehash（文件大小 + 首/尾各 64KB）。"""
    fmt, unit = "q", struct.calcsize("q")
    size = os.path.getsize(file_path)
    with open(file_path, "rb") as f:
        acc = size
        for offset in (0, max(0, size - _READ_CHUNK)):
            f.seek(offset)
            block = f.read(_READ_CHUNK)
            if len(block) < _READ_CHUNK:
                block += b"\x00" * (_READ_CHUNK - len(block))
            for i in range(0, _READ_CHUNK, unit):
                chunk = block[i:i + unit]
                if len(chunk) < unit:
                    chunk += b"\x00" * (unit - len(chunk))
                acc += struct.unpack(fmt, chunk)[0]
                acc &= 0xFFFFFFFFFFFFFFFF
    return f"{acc:016x}"


def _append_common_params(
    params: dict[str, str],
    *,
    languages: str | None,
    page: int,
    order_by: str | None,
    order_direction: str | None,
) -> None:
    if languages:
        params["languages"] = languages
    if page > 1:
        params["page"] = str(page)
    if order_by:
        params["order_by"] = order_by
    if order_direction:
        params["order_direction"] = order_direction


class OpenSubtitlesClient:
    """封装 ``GET /api/v1/subtitles`` 与 ``POST /api/v1/login``。"""

    def __init__(self) -> None:
        self.base_url = _normalize_base_url(config.OPEN_SUBTITLES_BASE_URL)

    def search_by_query(
        self,
        query: str,
        *,
        languages: str | None = None,
        page: int = 1,
        order_by: str | None = None,
        order_direction: str | None = None,
        title_match: str | None = None,
    ) -> dict[str, Any]:
        """文字搜索：``query``（及官方可选参数）。"""
        q = (query or "").strip()
        if not q:
            raise OpenSubtitlesError("query 不能为空")

        langs = languages or config.SUBTITLE_DEFAULT_LANGS or None
        params: dict[str, str] = {"query": q}
        _append_common_params(
            params, languages=langs, page=page, order_by=order_by, order_direction=order_direction
        )
        if title_match:
            params["title_match"] = title_match

        body = self._get_subtitles(params)
        return {"mode": "text", "query": q, **body}

    def search_by_hash(
        self,
        moviehash: str,
        *,
        languages: str | None = None,
        filename: str | None = None,
        page: int = 1,
        moviehash_match: str | None = None,
        order_by: str | None = None,
        order_direction: str | None = None,
    ) -> dict[str, Any]:
        """Hash 搜索：``moviehash``（及官方可选 ``filename`` 等）。"""
        h = (moviehash or "").strip().lower()
        if not h:
            raise OpenSubtitlesError("moviehash 不能为空")

        langs = languages or config.SUBTITLE_DEFAULT_LANGS or None
        params: dict[str, str] = {"moviehash": h}
        _append_common_params(
            params, languages=langs, page=page, order_by=order_by, order_direction=order_direction
        )
        if filename:
            params["filename"] = filename.strip()
        if moviehash_match:
            params["moviehash_match"] = moviehash_match

        body = self._get_subtitles(params)
        out: dict[str, Any] = {"mode": "hash", "moviehash": h, **body}
        if filename:
            out["filename"] = filename.strip()
        return out

    def _get_subtitles(self, params: dict[str, str]) -> dict[str, Any]:
        if not config.OPEN_SUBTITLES_API:
            raise OpenSubtitlesError("未配置 OPEN_SUBTITLES_API")
        return self._call("GET", "/api/v1/subtitles", params=params)

    def _call(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        auth: bool = True,
    ) -> dict[str, Any]:
        headers = {
            "Api-Key": config.OPEN_SUBTITLES_API,
            "User-Agent": config.OPEN_SUBTITLES_USER_AGENT,
            "Accept": "application/json",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        if auth:
            token = _auth.get("token")
            if not token or time.time() >= _auth.get("expires", 0):
                token = self._login()
            if token:
                headers["Authorization"] = f"Bearer {token}"

        try:
            resp = requests.request(
                method,
                f"{self.base_url}{path}",
                json=json_body,
                params=params,
                headers=headers,
                timeout=config.OPEN_SUBTITLES_TIMEOUT,
            )
        except requests.RequestException as e:
            raise OpenSubtitlesError(f"请求 OpenSubtitles 失败: {e}") from e

        try:
            data = resp.json()
        except ValueError:
            data = None

        if resp.status_code != 200:
            msg = "OpenSubtitles 请求失败"
            if isinstance(data, dict):
                msg = str(data.get("message") or data.get("msg") or msg)
            elif (resp.text or "").strip() and len(resp.text) < 500:
                msg = resp.text.strip()
            raise OpenSubtitlesError(msg, status_code=resp.status_code, payload=data)

        return data if isinstance(data, dict) else {}

    def _login(self) -> str | None:
        if not config.OPEN_SUBTITLES_USER or not config.OPEN_SUBTITLES_PASS:
            return None
        data = self._call(
            "POST",
            "/api/v1/login",
            json_body={
                "username": config.OPEN_SUBTITLES_USER,
                "password": config.OPEN_SUBTITLES_PASS,
            },
            auth=False,
        )
        token = data.get("token")
        if not token:
            raise OpenSubtitlesError("登录响应缺少 token")
        self.base_url = _normalize_base_url(data.get("base_url") or self.base_url)
        _auth["token"] = token
        _auth["expires"] = time.time() + _TOKEN_TTL
        return token


client = OpenSubtitlesClient()
