"""从字幕文件抽出纯文本。"""
from __future__ import annotations

import os
import re
from typing import Optional

_SUB_EXTS = {".vtt", ".srt", ".ass"}
_LANG_RANK = ("ai-zh", "zh-hans", "zh-cn", "zh-hant", "zh", "chi")
_TAG_RE = re.compile(r"<[^>]+>")
_SRT_TIME_RE = re.compile(r"\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}")


def pick_subtitle(directory: str, video_path: str) -> Optional[str]:
    """在视频旁边挑一条中文字幕，优先 vtt。"""
    stem = os.path.splitext(os.path.basename(video_path))[0]
    candidates: list[str] = []
    try:
        names = os.listdir(directory)
    except OSError:
        return None
    for name in names:
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext not in _SUB_EXTS or not name.startswith(stem):
            continue
        candidates.append(path)
    if not candidates:
        return None

    def rank(path: str) -> tuple:
        low = os.path.basename(path).lower()
        ext = os.path.splitext(low)[1]
        ext_rank = 0 if ext == ".vtt" else 1 if ext == ".srt" else 2
        lang_rank = len(_LANG_RANK)
        for index, key in enumerate(_LANG_RANK):
            if key in low:
                lang_rank = index
                break
        return (lang_rank, ext_rank, low)

    candidates.sort(key=rank)
    return candidates[0]


def cues_to_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        raw = handle.read()
    ext = os.path.splitext(path)[1].lower()
    if ext == ".srt":
        lines = _srt_lines(raw)
    else:
        lines = _vtt_lines(raw)
    return _dedupe(lines)


def _vtt_lines(raw: str) -> list[str]:
    lines: list[str] = []
    for line in raw.splitlines():
        text = line.strip().lstrip("\ufeff")
        if not text or text.startswith(("WEBVTT", "NOTE", "STYLE", "Kind:", "Language:")):
            continue
        if "-->" in text or text.isdigit():
            continue
        text = _TAG_RE.sub("", text).strip()
        if text:
            lines.append(text)
    return lines


def _srt_lines(raw: str) -> list[str]:
    lines: list[str] = []
    for line in raw.splitlines():
        text = line.strip().lstrip("\ufeff")
        if not text or text.isdigit() or _SRT_TIME_RE.search(text):
            continue
        text = _TAG_RE.sub("", text).strip()
        if text:
            lines.append(text)
    return lines


def _dedupe(lines: list[str]) -> str:
    kept: list[str] = []
    for line in lines:
        if kept and kept[-1] == line:
            continue
        kept.append(line)
    return "\n".join(kept)
