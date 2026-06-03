"""射手网 ASSRT API 客户端。

文档: https://secure.assrt.net/api/doc
"""

from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.parse import urlencode

from core.config import config
from core.tools.async_util import http_get_bytes

_PER_PAGE = 15
_TEXT_EXTS = (".srt", ".vtt", ".ass", ".ssa")
_DESC_EN = re.compile(r"英|english", re.I)
_DESC_ZH = re.compile(r"[简繁中]|国语|chs|cht", re.I)
_DESC_KO = re.compile(r"韩")


class AssrtError(Exception):

    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def _assrt_get(url: str, timeout: float, *, json_api: bool) -> tuple[int, bytes]:
    headers = {"Accept": "application/json"} if json_api else None
    try:
        return http_get_bytes(url, timeout=timeout, headers=headers)
    except TimeoutError as e:
        raise AssrtError(str(e) or "ASSRT 请求超时") from e
    except RuntimeError as e:
        msg = str(e)
        low = msg.lower()
        if "recursion" in low:
            raise AssrtError("ASSRT 请求异常（进程初始化冲突，请重启服务后再试）") from e
        if "timeout" in low or "timed out" in low:
            raise AssrtError(f"ASSRT 请求超时（{int(timeout)}s）") from e
        raise AssrtError(msg) from e


def _http_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    token = (config.ASSRT_API_KEY or "").strip()
    if not token:
        raise AssrtError("未配置 ASSRT_API_KEY")

    base = (config.ASSRT_BASE_URL or "https://api.assrt.net").rstrip("/")
    url = f"{base}{path}?{urlencode({**params, 'token': token})}"
    timeout = float(config.ASSRT_TIMEOUT)

    _http_status, body = _assrt_get(url, timeout, json_api=True)
    try:
        data = json.loads(body.decode("utf-8", errors="replace")) if body else {}
    except ValueError as e:
        raise AssrtError(f"ASSRT 响应非 JSON: HTTP {_http_status}") from e
    if not isinstance(data, dict):
        raise AssrtError("ASSRT 响应格式错误")
    status = data.get("status", 0)
    if status == 0:
        return data
    if status == 20001:
        raise AssrtError("ASSRT Token 无效，请检查 ASSRT_API_KEY", status_code=status, payload=data)
    if status == 30900:
        raise AssrtError("ASSRT 请求过于频繁，请稍后再试", status_code=status, payload=data)
    if status == 101:
        raise AssrtError("搜索关键词至少 3 个字符", status_code=status, payload=data)
    for block in data.values():
        if isinstance(block, dict) and block.get("result") == "failed":
            err = block.get("err") or block.get("message")
            if err:
                raise AssrtError(str(err), status_code=status, payload=data)
    raise AssrtError(f"ASSRT 请求失败 (status={status})", status_code=status, payload=data)


def _want_langs(languages: str | None) -> set[str]:
    raw = languages or config.SUBTITLE_DEFAULT_LANGS or ""
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def _lang_desc(sub: dict[str, Any]) -> str:
    raw = sub.get("lang")
    if not isinstance(raw, dict):
        return ""
    return str(raw.get("desc") or "").strip()


def _lang_ok(sub: dict[str, Any], want: set[str]) -> bool:
    if not want:
        return True
    desc = _lang_desc(sub)
    if not desc:
        return True
    if ("en" in want or "eng" in want) and _DESC_EN.search(desc):
        return True
    if want & {"zh", "chs", "cht", "chi", "zho"} and _DESC_ZH.search(desc):
        return True
    if want & {"ko", "kor"} and _DESC_KO.search(desc):
        return True
    if not (("en" in want or "eng" in want) or want & {"zh", "chs", "cht", "chi", "zho"} or want & {"ko", "kor"}):
        return True
    return False


def _row(sub: dict[str, Any]) -> dict[str, Any]:
    sid = sub.get("id")
    sub_id = str(sid) if sid is not None else ""
    release = str(sub.get("native_name") or sub.get("videoname") or "")
    fname = str(sub.get("videoname") or release or sub_id)
    subtype = str(sub.get("subtype") or "")
    if subtype:
        fname = f"{fname} ({subtype})"
    return {
        "id": sub_id,
        "type": "subtitle",
        "attributes": {
            "subtitle_id": sub_id,
            "language": _lang_desc(sub),
            "release": release,
            "files": [{
                "file_id": sid,
                "file_name": fname
            }],
        },
    }


def _subs_from_block(block: dict[str, Any]) -> list[Any]:
    raw = block.get("subs")
    if not isinstance(raw, list):
        return []
    return list(raw)


def _page_payload(subs: list[Any], page: int, want: set[str]) -> dict[str, Any]:
    rows = [_row(s) for s in subs if isinstance(s, dict) and _lang_ok(s, want)]
    has_more = len(subs) >= _PER_PAGE
    total_pages = (page + 1) if has_more else page
    if page > 1 and not rows and not subs:
        total_pages = page - 1
    return {
        "total_count": len(rows),
        "total_pages": max(1, total_pages),
        "page": page,
        "per_page": _PER_PAGE,
        "data": rows,
    }


class AssrtClient:

    def search_by_query(
        self,
        query: str,
        *,
        languages: str | None = None,
        page: int = 1,
    ) -> dict[str, Any]:
        q = (query or "").strip()
        if len(q) < 3:
            raise AssrtError("搜索关键词至少 3 个字符")
        page = max(1, page)
        data = _http_get("/v1/sub/search", {
            "q": q,
            "pos": (page - 1) * _PER_PAGE,
            "cnt": _PER_PAGE,
        })
        block = data.get("sub")
        if not isinstance(block, dict):
            raise AssrtError("ASSRT 搜索响应缺少 sub")
        return {
            "mode": "text",
            "query": q,
            **_page_payload(_subs_from_block(block), page, _want_langs(languages)),
        }

    def search_by_filename(
        self,
        filename: str,
        *,
        languages: str | None = None,
        page: int = 1,
    ) -> dict[str, Any]:
        name = (filename or "").strip()
        if not name:
            raise AssrtError("filename 不能为空")
        dot = name.rfind(".")
        q = name[:dot] if dot > 0 else name
        if len(q) < 3:
            raise AssrtError("搜索关键词至少 3 个字符")
        page = max(1, page)
        data = _http_get("/v1/sub/search", {
            "q": q,
            "pos": (page - 1) * _PER_PAGE,
            "cnt": _PER_PAGE,
            "is_file": 1,
            "no_muxer": 1,
        })
        block = data.get("sub")
        if not isinstance(block, dict):
            raise AssrtError("ASSRT 搜索响应缺少 sub")
        return {
            "mode": "hash",
            "filename": name,
            **_page_payload(_subs_from_block(block), page, _want_langs(languages)),
        }

    def download_to_sidecar(
        self,
        sub_id: str | int,
        video_path: str,
        *,
        file_index: int = 0,
    ) -> dict[str, Any]:
        sid = str(sub_id).strip()
        if not sid:
            raise AssrtError("字幕 id 不能为空")

        data = _http_get("/v1/sub/detail", {"id": sid})
        block = data.get("sub")
        if not isinstance(block, dict):
            raise AssrtError("ASSRT 详情响应缺少 sub")
        subs = block.get("subs")
        if not isinstance(subs, list) or not subs or not isinstance(subs[0], dict):
            raise AssrtError("字幕不存在", status_code=20900)
        detail = subs[0]

        dl_url = ""
        remote_name = "subtitle.srt"
        filelist = detail.get("filelist")
        if isinstance(filelist, list) and filelist:
            candidates = [f for f in filelist if isinstance(f, dict) and f.get("url")]
            candidates.sort(key=lambda f: (
                0 if str(f.get("f", "")).lower().endswith(_TEXT_EXTS) else 1,
                str(f.get("f", "")),
            ), )
            if not candidates:
                raise AssrtError("字幕包内无可用文件")
            item = candidates[min(max(0, file_index), len(candidates) - 1)]
            dl_url = str(item["url"])
            remote_name = str(item.get("f") or remote_name)
        elif detail.get("url"):
            remote_name = str(detail.get("filename") or remote_name)
            if remote_name.lower().endswith(".rar"):
                raise AssrtError("该字幕仅为压缩包，请换一条含 srt 的结果")
            dl_url = str(detail["url"])
        else:
            raise AssrtError("未找到字幕下载地址")

        timeout = float(config.ASSRT_TIMEOUT)
        dl_status, content = _assrt_get(dl_url, timeout, json_api=False)
        if dl_status != 200:
            raise AssrtError(f"下载字幕失败: HTTP {dl_status}")

        ext = os.path.splitext(remote_name)[1].lower()
        if ext not in _TEXT_EXTS:
            ext = ".srt"
        last_dot = video_path.rfind(".")
        if last_dot <= 0:
            raise AssrtError("无效的视频路径")
        base = video_path[:last_dot]

        want = _want_langs(config.SUBTITLE_DEFAULT_LANGS)
        if want == {"en"} or (want & {"en", "eng"} and not (want & {"zh", "chs", "cht"})):
            out_path = f"{base}.en{ext}"
        elif want & {"zh", "chs", "cht"}:
            out_path = f"{base}.zh{ext}"
        else:
            out_path = f"{base}{ext}"

        with open(out_path, "wb") as f:
            f.write(content)

        return {"path": out_path, "remote_name": remote_name, "subtitle_id": sid}


client = AssrtClient()
