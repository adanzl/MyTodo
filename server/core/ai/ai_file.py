"""Dify 图片文件上传与能力自检。

对话要带图片时，Dify Service API 只接受两种入站形态：

- ``local_file``：文件先上传到 Dify，消息里引用 ``upload_file_id``（本模块走这条）；
- ``remote_url``：给一个 Dify 能抓取的 URL。

浏览器不能持有 Dify app key，所以「换成 Dify 的 id」这步必须在服务端完成。图片
本身由前端调既有 ``/api/pic/upload`` 存进 pic 目录，本模块只负责把该文件转发给
Dify。

两个实测过的 Dify 侧行为决定了这里的写法：

1. 应用「文件上传」开关关闭时，带 ``files`` 调 /chat-messages **不报错**，附件被
   静默丢弃 ⇒ 发送前必须先自检 ``file_upload.enabled``，否则用户以为发出去了；
2. ``upload_file_id`` 可跨消息复用 ⇒ 按 ``(user, filename)`` 缓存，避免重复上传。

第 2 点同时意味着：图片文件名会被原样保留在 Dify 的历史消息里，前端可据此用
``/api/pic/view?name=<filename>`` 直接渲染，无需额外映射表。
"""

from __future__ import annotations

import mimetypes
import os
import threading
import time

import requests

from core.ai.ai_local import API_URL, dify_api_key, dify_headers
from core.config import app_logger
from core.services.pic_mgr import pic_mgr

log = app_logger

# 能力自检结果缓存时长（秒）：期间内不重复请求 /parameters
CAPABILITY_TTL = 300
# 「未开启」的缓存要短：读到未开启通常正说明用户正在 Dify 里配置。
# 若按常规 TTL 缓存，用户改完开关后还会连着失败几分钟，很难判断到底哪里没生效。
CAPABILITY_TTL_DISABLED = 30
# upload_file_id 缓存条数上限（进程内，仅用于省掉重复上传）
MAX_ID_CACHE = 500
# 与 Dify 通信的超时（秒）
REQUEST_TIMEOUT = 30


class AiImageError(Exception):
    """图片无法用于 Dify 对话（能力未开 / 上传失败 / 文件不合法）。

    ``str(err)`` 是面向用户的文案，直接经 socket error 事件展示。
    """


# (user, filename) -> upload_file_id
_id_cache: dict[tuple[str, str], str] = {}
# user -> (到期时间, 是否开启, 图片数上限)
_capability_cache: dict[str, tuple[float, bool, int]] = {}
_lock = threading.Lock()


# ---------------- 能力自检 ----------------


def image_capability(user: str, *, force: bool = False) -> tuple[bool, int]:
    """读取该应用的图片上传能力，返回 ``(是否开启, 单条消息图片上限)``。

    Dify 在开关关闭时静默丢弃附件，所以这不是可选优化，而是必需的显式检查。
    上限为 0 表示上游未给出限制。
    """
    key = user or ""
    now = time.time()
    if not force:
        with _lock:
            hit = _capability_cache.get(key)
        if hit and now < hit[0]:
            return hit[1], hit[2]

    enabled, limit = _fetch_capability(key)
    ttl = CAPABILITY_TTL if enabled else CAPABILITY_TTL_DISABLED
    with _lock:
        _capability_cache[key] = (now + ttl, enabled, limit)
    return enabled, limit


def _fetch_capability(user: str) -> tuple[bool, int]:
    """请求 /parameters 解析能力。读不到时放行，交给真实发送结果兜底。"""
    try:
        with requests.get(
            f"{API_URL}/parameters",
            headers=dify_headers(user),
            timeout=REQUEST_TIMEOUT,
        ) as rsp:
            rsp.raise_for_status()
            data = rsp.json() or {}
    except (requests.exceptions.RequestException, ValueError) as e:
        log.warning(f"[AI] 读取 Dify 应用参数失败，跳过图片能力自检: {e}")
        return True, 0

    upload = data.get("file_upload")
    if not isinstance(upload, dict) or not upload.get("enabled"):
        return False, 0

    # 部分版本没有 image 子对象，此时以顶层 enabled 为准
    image = upload.get("image")
    if isinstance(image, dict) and not image.get("enabled", True):
        return False, 0

    raw_limit = None
    if isinstance(image, dict):
        raw_limit = image.get("number_limits")
    if raw_limit is None:
        raw_limit = upload.get("number_limits")
    try:
        limit = int(raw_limit or 0)
    except (TypeError, ValueError):
        limit = 0
    return True, max(limit, 0)


# ---------------- 取本地图片 ----------------


def _read_pic_file(filename: str) -> tuple[bytes, str]:
    """读取 pic 目录中的图片，返回 ``(字节, mime)``。"""
    abs_path, err = pic_mgr.validate_path(filename)
    if abs_path is None:
        # validate_path 同时做了扩展名白名单与目录穿越防护
        raise AiImageError(f"图片文件名不合法：{err}")
    if not os.path.isfile(abs_path):
        raise AiImageError("图片不存在，请重新选择")
    try:
        with open(abs_path, "rb") as fp:
            data = fp.read()
    except OSError as e:
        raise AiImageError(f"读取图片失败：{e}") from e
    if not data:
        raise AiImageError("图片内容为空，请重新选择")
    mime = mimetypes.guess_type(abs_path)[0] or "image/png"
    return data, mime


# ---------------- 上传到 Dify ----------------


def upload_image(filename: str, user: str) -> str:
    """把 pic 目录里的图片上传到 Dify，返回 ``upload_file_id``（带缓存）。"""
    key = (user or "", filename)
    with _lock:
        cached = _id_cache.get(key)
    if cached:
        return cached

    data, mime = _read_pic_file(filename)
    file_name = os.path.basename(filename)

    try:
        # 注意：这里是 multipart，不能复用 dify_headers（它带 application/json）
        with requests.post(
            f"{API_URL}/files/upload",
            headers={"Authorization": f"Bearer {dify_api_key(user)}"},
            files={"file": (file_name, data, mime)},
            data={"user": user or ""},
            timeout=REQUEST_TIMEOUT,
        ) as rsp:
            if rsp.status_code >= 400:
                raise AiImageError(_upload_error_message(rsp))
            payload = rsp.json() or {}
    except requests.exceptions.RequestException as e:
        raise AiImageError(f"上传图片到 AI 服务失败：{e}") from e

    file_id = payload.get("id")
    if not file_id:
        raise AiImageError("上传图片失败：AI 服务未返回文件 id")

    with _lock:
        if len(_id_cache) >= MAX_ID_CACHE:
            _id_cache.clear()
        _id_cache[key] = file_id
    log.info(f"[AI] 图片已上传 Dify: user={user} file={file_name} id={file_id}")
    return file_id


def _upload_error_message(rsp: requests.Response) -> str:
    """把 Dify 的上传错误码翻成可读中文。"""
    try:
        body = rsp.json() or {}
    except ValueError:
        body = {}
    code = body.get("code") or ""
    message = body.get("message") or ""
    if code == "file_too_large":
        return "图片太大，超出 AI 服务限制"
    if code == "unsupported_file_type":
        return "AI 服务不支持该图片格式，请改用 JPG/PNG"
    if code == "file_extension_blocked":
        return "AI 服务禁止该图片格式，请改用 JPG/PNG"
    return f"上传图片失败：{message or code or rsp.status_code}"


# ---------------- 供对话调用 ----------------


def _parse_raw_files(raw) -> list[str]:
    """前端只传文件名；容忍字符串、对象与非法项，并去掉路径成分。"""
    if not raw:
        return []
    if isinstance(raw, (str, dict)):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return []

    names: list[str] = []
    for item in raw:
        name = ""
        if isinstance(item, str):
            name = item
        elif isinstance(item, dict):
            name = str(item.get("filename") or "")
        name = os.path.basename(name.strip())
        if name:
            names.append(name)
    return names


def resolve_chat_files(raw_files, user: str) -> list[dict]:
    """把前端传来的图片列表解析成 Dify ``/chat-messages`` 的 ``files`` 参数。

    Raises:
        AiImageError: 能力未开、张数超限或任一图片上传失败。
    """
    names = _parse_raw_files(raw_files)
    if not names:
        return []

    enabled, limit = image_capability(user)
    if not enabled:
        raise AiImageError(
            "当前机器人未开启图片功能，请在 Dify 应用里打开「文件上传」并发布"
        )
    if limit and len(names) > limit:
        raise AiImageError(f"最多只能发送 {limit} 张图片")

    return [
        {
            "type": "image",
            "transfer_method": "local_file",
            "upload_file_id": upload_image(name, user),
        }
        for name in names
    ]
