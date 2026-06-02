"""字幕服务：sidecar 字幕发现、OpenSubtitles 在线搜索。"""

from __future__ import annotations

import os
from typing import Any

from core.config import app_logger, config
from core.tools.open_subtitles import (
    OpenSubtitlesError,
    client as open_subtitles_client,
    compute_movie_hash,
)
from core.utils import (
    _err,
    _ok,
    subtitle_label_from_path,
    subtitle_lang_from_path,
    validate_and_normalize_path,
)

log = app_logger

_SUBTITLE_SUFFIXES = ("", ".zh", ".chs", ".cht", ".en", ".eng")
_SUBTITLE_EXTS = (".vtt", ".srt")


class SubtitleMgr:
    """字幕相关业务逻辑。"""

    def __init__(self) -> None:
        """初始化，读取默认媒体根目录。"""
        self.default_base_dir = config.DEFAULT_BASE_DIR

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

    def search_by_text(
        self,
        query: str,
        *,
        languages: str | None = None,
        page: int = 1,
        order_by: str | None = None,
        order_direction: str | None = None,
        title_match: str | None = None,
    ) -> dict[str, Any]:
        """文字搜索（透传 OpenSubtitles ``GET /api/v1/subtitles`` 响应）。"""
        try:
            return _ok(open_subtitles_client.search_by_query(
                query,
                languages=languages,
                page=page,
                order_by=order_by,
                order_direction=order_direction,
                title_match=title_match,
            ))
        except OpenSubtitlesError as e:
            log.warning(f"[SUBTITLE] text search failed: {e}")
            return _err(str(e))
        except Exception as e:
            log.error(f"[SUBTITLE] text search failed: {e}")
            return _err(f"search subtitle failed: {e}")

    def search_by_video_path(
        self,
        video_path: str,
        *,
        languages: str | None = None,
        filename: str | None = None,
        page: int = 1,
        moviehash_match: str | None = None,
        order_by: str | None = None,
        order_direction: str | None = None,
    ) -> dict[str, Any]:
        """按本地视频路径搜索字幕：服务端计算 moviehash 后请求 OpenSubtitles。"""
        try:
            path = (video_path or "").strip()
            if not path:
                return _err("video_path 不能为空")

            normalized, error_msg = validate_and_normalize_path(
                path, self.default_base_dir, must_be_file=True
            )
            if not normalized:
                return _err(error_msg or "Invalid video_path")

            try:
                m_hash = compute_movie_hash(normalized)
            except OSError as e:
                return _err(f"无法读取视频文件: {e}")

            fname = (filename or "").strip() or os.path.basename(normalized)

            payload = open_subtitles_client.search_by_hash(
                m_hash,
                languages=languages,
                filename=fname,
                page=page,
                moviehash_match=moviehash_match,
                order_by=order_by,
                order_direction=order_direction,
            )
            return _ok({"video_path": normalized, **payload})
        except OpenSubtitlesError as e:
            log.warning(f"[SUBTITLE] hash search failed: {e}")
            return _err(str(e))
        except RecursionError:
            log.error("[SUBTITLE] hash search failed: path or file caused recursion")
            return _err("search subtitle failed: 视频路径或文件异常，无法计算 hash")
        except Exception as e:
            log.error(f"[SUBTITLE] hash search failed: {e}")
            return _err(f"search subtitle failed: {e}")


subtitle_mgr = SubtitleMgr()
