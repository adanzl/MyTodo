"""OpenSubtitles.com REST API 客户端。

文档: https://opensubtitles.stoplight.io/docs/opensubtitles-api/a172317bd5ccc-search-for-subtitles

HTTP 在 spawn 子进程执行：gevent 会全局 patch ssl，原生线程里 requests 仍会 SSL 递归；
spawn 启动干净解释器，未 patch。
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import stat
import struct
import threading
import time
from typing import Any

from core.config import config

_SPAWN_CTX = mp.get_context("spawn")

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


def _spawn_do_request(
    out_q: Any,
    method: str,
    url: str,
    headers: dict[str, str],
    json_body: dict[str, Any] | None,
    params: dict[str, str] | None,
    timeout: float,
) -> None:
    """子进程入口（须为模块级函数以便 spawn 序列化）。"""
    import requests as req

    try:
        resp = req.request(
            method,
            url,
            json=json_body,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        out_q.put(("ok", resp.status_code, resp.text))
    except Exception as exc:
        out_q.put(("err", type(exc).__name__, str(exc)))


def _request_in_spawn(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
    timeout: float | None = None,
) -> tuple[int, str]:
    """在 spawn 子进程发 HTTP，返回 (status_code, response_text)。"""
    req_timeout = timeout if timeout is not None else float(config.OPEN_SUBTITLES_TIMEOUT)
    wait = req_timeout + 15
    out_q = _SPAWN_CTX.Queue()
    proc = _SPAWN_CTX.Process(
        target=_spawn_do_request,
        args=(out_q, method, url, headers, json_body, params, req_timeout),
    )
    proc.start()
    proc.join(wait)
    if proc.is_alive():
        proc.kill()
        proc.join(2)
        raise TimeoutError(f"操作超时 ({wait}s)")

    msg = out_q.get()
    if msg[0] == "err":
        raise OpenSubtitlesError(f"请求 OpenSubtitles 失败: {msg[2]}")
    return int(msg[1]), str(msg[2])


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

        url = f"{self.base_url}{path}"
        try:
            status, text = _request_in_spawn(
                method,
                url,
                headers=headers,
                json_body=json_body,
                params=params,
                timeout=float(config.OPEN_SUBTITLES_TIMEOUT),
            )
        except TimeoutError as e:
            raise OpenSubtitlesError("请求 OpenSubtitles 超时") from e

        try:
            data = json.loads(text) if text else None
        except ValueError:
            data = None

        if status != 200:
            msg = "OpenSubtitles 请求失败"
            if isinstance(data, dict):
                msg = str(data.get("message") or data.get("msg") or msg)
            elif text.strip() and len(text) < 500:
                msg = text.strip()
            raise OpenSubtitlesError(msg, status_code=status, payload=data)

        return data if isinstance(data, dict) else {}


client = OpenSubtitlesClient()
