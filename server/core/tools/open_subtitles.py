"""OpenSubtitles.com REST API 客户端。

文档: https://opensubtitles.stoplight.io/docs/opensubtitles-api/a172317bd5ccc-search-for-subtitles
"""

from __future__ import annotations

import os
import stat
import struct
import threading
import time
from typing import Any

import requests

from core.config import config

_READ_CHUNK = 64 * 1024
_TOKEN_TTL = 23 * 3600
_auth: dict[str, Any] = {"token": None, "expires": 0.0}
_auth_lock = threading.Lock()


class OpenSubtitlesError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def _normalize_base_url(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if not u:
        return "https://api.opensubtitles.com"
    if not u.startswith(("http://", "https://")):
        return "https://" + u.lstrip("/")
    return u


def compute_movie_hash(file_path: str) -> str:
    """OpenSubtitles moviehash（文件大小 + 首/尾各 64KB）。"""
    try:
        st = os.lstat(file_path)
    except (RecursionError, OSError) as e:
        raise OSError("无法读取视频文件") from e
    if not stat.S_ISREG(st.st_mode):
        raise OSError("不是普通文件")

    size = st.st_size
    offsets = [0]
    if size > _READ_CHUNK:
        offsets.append(size - _READ_CHUNK)

    acc = size
    try:
        with open(file_path, "rb") as f:
            for offset in offsets:
                f.seek(offset)
                block = f.read(_READ_CHUNK)
                if len(block) < _READ_CHUNK:
                    block += b"\x00" * (_READ_CHUNK - len(block))
                for i in range(0, _READ_CHUNK, 8):
                    acc += struct.unpack_from("q", block, i)[0]
                    acc &= 0xFFFFFFFFFFFFFFFF
    except RecursionError as e:
        raise OSError("无法读取视频文件") from e
    return f"{acc:016x}"


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
        q = (query or "").strip()
        if not q:
            raise OpenSubtitlesError("query 不能为空")

        langs = languages or config.SUBTITLE_DEFAULT_LANGS or None
        params: dict[str, str] = {"query": q}
        if langs:
            params["languages"] = langs
        if page > 1:
            params["page"] = str(page)
        if order_by:
            params["order_by"] = order_by
        if order_direction:
            params["order_direction"] = order_direction
        if title_match:
            params["title_match"] = title_match

        return {"mode": "text", "query": q, **self._get_json("/api/v1/subtitles", params=params)}

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
        h = (moviehash or "").strip().lower()
        if not h:
            raise OpenSubtitlesError("moviehash 不能为空")

        langs = languages or config.SUBTITLE_DEFAULT_LANGS or None
        params: dict[str, str] = {"moviehash": h}
        if langs:
            params["languages"] = langs
        if page > 1:
            params["page"] = str(page)
        if order_by:
            params["order_by"] = order_by
        if order_direction:
            params["order_direction"] = order_direction
        fname = (filename or "").strip()
        if fname:
            params["filename"] = fname
        if moviehash_match:
            params["moviehash_match"] = moviehash_match

        out: dict[str, Any] = {"mode": "hash", "moviehash": h, **self._get_json("/api/v1/subtitles", params=params)}
        if fname:
            out["filename"] = fname
        return out

    def _get_json(self, path: str, *, params: dict[str, str] | None = None) -> dict[str, Any]:
        if not config.OPEN_SUBTITLES_API:
            raise OpenSubtitlesError("未配置 OPEN_SUBTITLES_API")

        token = self._token()
        for retry in (False, True):
            try:
                return self._http("GET", path, params=params, token=token)
            except OpenSubtitlesError as e:
                if retry or not token or e.status_code not in (401, 403):
                    raise
                with _auth_lock:
                    _auth["token"] = None
                    _auth["expires"] = 0.0
                token = self._token()
        raise OpenSubtitlesError("请求失败")

    def _token(self) -> str | None:
        if not config.OPEN_SUBTITLES_USER or not config.OPEN_SUBTITLES_PASS:
            return None
        with _auth_lock:
            token = _auth.get("token")
            if token and time.time() < _auth.get("expires", 0):
                return token

            data = self._http(
                "POST",
                "/api/v1/login",
                json_body={
                    "username": config.OPEN_SUBTITLES_USER,
                    "password": config.OPEN_SUBTITLES_PASS,
                },
            )
            token = data.get("token")
            if not token:
                raise OpenSubtitlesError("登录响应缺少 token")
            self.base_url = _normalize_base_url(data.get("base_url") or self.base_url)
            _auth["token"] = token
            _auth["expires"] = time.time() + _TOKEN_TTL
            return token

    def _http(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Api-Key": config.OPEN_SUBTITLES_API,
            "User-Agent": config.OPEN_SUBTITLES_USER_AGENT,
            "Accept": "application/json",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"
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
        except RecursionError as e:
            raise OpenSubtitlesError(f"请求 OpenSubtitles 失败: {e}") from e
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


client = OpenSubtitlesClient()
