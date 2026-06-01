"""媒体文件服务：时长查询、文件下发、字幕发现。"""

from __future__ import annotations

import os
from typing import Any

from core.config import MIMETYPE_MAP, app_logger, config
from core.utils import (
    _err,
    _ok,
    get_media_duration,
    subtitle_label_from_path,
    subtitle_lang_from_path,
    validate_and_normalize_path,
)

log = app_logger

_SUBTITLE_SUFFIXES = ("", ".zh", ".chs", ".cht", ".en", ".eng")
_SUBTITLE_EXTS = (".vtt", ".srt")


class MediaMgr:
    """媒体文件相关业务逻辑。"""

    def __init__(self) -> None:
        """初始化，读取默认媒体根目录。"""
        self.default_base_dir = config.DEFAULT_BASE_DIR

    def get_duration(self, file_path: str) -> dict[str, Any]:
        """获取媒体文件时长（ffprobe）。

        Args:
            file_path: 媒体文件路径（相对或绝对）

        Returns:
            成功: {"code": 0, "data": {"duration": float, "path": str}}
            失败: {"code": -1, "msg": str}
        """
        try:
            normalized_path, error_msg = validate_and_normalize_path(
                file_path, self.default_base_dir, must_be_file=True
            )
            if not normalized_path:
                return _err(error_msg or "Invalid file path")

            duration = get_media_duration(normalized_path)
            if duration is None:
                return _err("无法获取媒体文件时长")
            return _ok({"duration": duration, "path": normalized_path})
        except PermissionError as e:
            log.error(f"Permission denied for {file_path}: {e}")
            return _err(f"Permission denied: {e}")
        except Exception as e:
            log.error(f"Error getting media duration: {e}")
            return _err(f"Error: {e}")

    def prepare_serve_file(self, filepath: str) -> dict[str, Any]:
        """校验媒体文件并返回下发所需的 path 与 MIME。

        Args:
            filepath: URL 中的文件路径

        Returns:
            成功: {"code": 0, "data": {"path": str, "mimetype": str}}
            失败: {"code": -1, "msg": str, "http_status": int}（供路由层 abort）
        """
        try:
            filepath = filepath.replace("../", "").replace("..\\", "")
            if not filepath.startswith("/"):
                filepath = "/" + filepath

            if not os.path.isfile(filepath):
                log.warning(f"[MEDIA] File not found: {filepath}")
                return {**_err("File not found"), "http_status": 404}

            ext = os.path.splitext(filepath)[1].lower()
            mimetype = MIMETYPE_MAP.get(ext, "application/octet-stream")
            log.info(f"[MEDIA] Serving file: {filepath} (MIME: {mimetype})")
            return _ok({"path": filepath, "mimetype": mimetype})
        except Exception as e:
            log.error(f"[MEDIA] Error preparing file {filepath}: {e}")
            return {**_err(str(e)), "http_status": 500}

    def resolve_subtitles(self, video_path: str) -> dict[str, Any]:
        """查找视频同目录下实际存在的 sidecar 字幕。

        Args:
            video_path: 视频文件路径

        Returns:
            成功: {"code": 0, "data": {"tracks": [{path, label, lang, ext}, ...]}}
            失败: {"code": -1, "msg": str}
        """
        try:
            normalized_video, error_msg = validate_and_normalize_path(
                video_path, self.default_base_dir, must_be_file=True
            )
            if not normalized_video:
                return _err(error_msg or "Invalid video_path")

            tracks: list[dict[str, Any]] = []
            last_dot = normalized_video.rfind(".")
            candidates: list[str] = []
            if last_dot > 0:
                base = normalized_video[:last_dot]
                candidates = [
                    f"{base}{suffix}{ext}"
                    for suffix in _SUBTITLE_SUFFIXES
                    for ext in _SUBTITLE_EXTS
                ]
            for candidate in candidates:
                ext = os.path.splitext(candidate)[1].lower()
                if ext not in _SUBTITLE_EXTS:
                    continue

                normalized, _ = validate_and_normalize_path(
                    candidate, self.default_base_dir, must_be_file=True
                )
                if not normalized or not os.path.isfile(normalized):
                    continue

                tracks.append({
                    "path": normalized,
                    "label": subtitle_label_from_path(normalized),
                    "lang": subtitle_lang_from_path(normalized),
                    "ext": ext.lstrip("."),
                })

            return _ok({"tracks": tracks})
        except Exception as e:
            log.error(f"[SUBTITLE] resolve failed: {e}")
            return _err(f"resolve subtitle failed: {e}")


media_mgr = MediaMgr()
