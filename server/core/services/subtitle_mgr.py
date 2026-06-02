"""字幕服务：sidecar 发现、ASSRT 搜索下载、Whisper 识别。"""

from __future__ import annotations

import os
from typing import Any

from core.config import app_logger, config
from core.subtitles import AssrtError, WhisperError, assrt_client, transcribe_to_sidecar
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
        self.default_base_dir = config.DEFAULT_BASE_DIR

    def resolve_subtitles(self, video_path: str) -> dict[str, Any]:
        try:
            normalized_video, error_msg = validate_and_normalize_path(
                video_path, self.default_base_dir, must_be_file=True
            )
            if not normalized_video:
                return _err(error_msg or "Invalid video_path")

            tracks: list[dict[str, Any]] = []
            last_dot = normalized_video.rfind(".")
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
        q = (query or "").strip()
        if not q:
            return _err("query 不能为空")
        try:
            payload = assrt_client.search_by_query(
                q,
                languages=languages,
                page=page,
                order_by=order_by,
                order_direction=order_direction,
                title_match=title_match,
            )
            return _ok(payload)
        except RecursionError:
            log.exception("[SUBTITLE] ASSRT recursion, query=%s", q)
            return _err("search subtitle failed: 在线搜索请求异常")
        except AssrtError as e:
            log.warning(f"[SUBTITLE] text search failed: {e}")
            return _err(str(e))
        except Exception as e:
            log.error(f"[SUBTITLE] text search failed: {e}")
            return _err(f"search subtitle failed: {e}")

    def recognize_subtitle(
        self,
        video_path: str,
        *,
        language: str = "en",
    ) -> dict[str, Any]:
        """Whisper 语音识别，写入视频同目录 sidecar 字幕。"""
        path = (video_path or "").strip()
        if not path:
            return _err("video_path 不能为空")

        normalized, error_msg = validate_and_normalize_path(
            path, self.default_base_dir, must_be_file=True
        )
        if not normalized:
            return _err(error_msg or "Invalid video_path")

        lang = (language or "en").strip().lower() or "en"
        try:
            result = transcribe_to_sidecar(normalized, language=lang)
        except WhisperError as e:
            log.warning(f"[SUBTITLE] recognize failed: {e}")
            return _err(str(e))
        except Exception as e:
            log.error(f"[SUBTITLE] recognize failed: {e}")
            return _err(f"语音识别失败: {e}")

        return _ok({
            "video_path": normalized,
            **result,
            "label": subtitle_label_from_path(result["path"]),
            "lang": subtitle_lang_from_path(result["path"]),
            "ext": os.path.splitext(result["path"])[1].lstrip(".").lower(),
        })

    def download_subtitle(
        self,
        video_path: str,
        subtitle_id: str,
        *,
        file_index: int = 0,
    ) -> dict[str, Any]:
        path = (video_path or "").strip()
        sid = (subtitle_id or "").strip()
        if not path:
            return _err("video_path 不能为空")
        if not sid:
            return _err("subtitle_id 不能为空")

        normalized, error_msg = validate_and_normalize_path(
            path, self.default_base_dir, must_be_file=True
        )
        if not normalized:
            return _err(error_msg or "Invalid video_path")

        try:
            result = assrt_client.download_to_sidecar(
                sid,
                normalized,
                file_index=file_index,
            )
        except AssrtError as e:
            log.warning(f"[SUBTITLE] download failed: {e}")
            return _err(str(e))
        except OSError as e:
            return _err(f"写入字幕文件失败: {e}")
        except Exception as e:
            log.error(f"[SUBTITLE] download failed: {e}")
            return _err(f"download subtitle failed: {e}")

        return _ok({
            "video_path": normalized,
            **result,
            "label": subtitle_label_from_path(result["path"]),
            "lang": subtitle_lang_from_path(result["path"]),
            "ext": os.path.splitext(result["path"])[1].lstrip(".").lower(),
        })


subtitle_mgr = SubtitleMgr()
