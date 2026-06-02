"""Whisper 本地语音识别，生成 sidecar 字幕。"""

from __future__ import annotations

import os
import tempfile
from typing import Any, Iterable

from core.config import config
from core.tools.async_util import run_blocking
from core.utils import run_subprocess_safe

_ZH_LANGS = frozenset({"zh", "chs", "cht", "chi", "zho"})


class WhisperError(Exception):
    pass


def _vtt_ts(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _segments_to_vtt(segments: Iterable[Any]) -> str:
    cues: list[str] = []
    for seg in segments:
        text = str(getattr(seg, "text", "") or "").strip()
        if not text:
            continue
        start = float(getattr(seg, "start", 0))
        end = float(getattr(seg, "end", start))
        cues.append(f"{_vtt_ts(start)} --> {_vtt_ts(end)}\n{text}\n")
    return "WEBVTT\n\n" + "".join(cues)


def _sidecar_path(video_path: str, language: str) -> str:
    base, _ = os.path.splitext(video_path)
    if not base:
        raise WhisperError("无效的视频路径")
    lang = (language or "en").strip().lower()
    if lang in ("en", "eng"):
        return f"{base}.en.vtt"
    if lang in _ZH_LANGS:
        return f"{base}.zh.vtt"
    return f"{base}.vtt"


def _whisper_transcribe(wav_path: str, language: str) -> str:

    def _work() -> str:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-untyped]
        except ImportError as e:
            raise WhisperError("未安装 faster-whisper，请执行: pip install faster-whisper") from e

        model = WhisperModel(
            (config.WHISPER_MODEL or "base").strip(),
            device=(config.WHISPER_DEVICE or "cpu").strip(),
            compute_type=(config.WHISPER_COMPUTE_TYPE or "int8").strip(),
        )
        lang = (language or "en").strip() or None
        seg_list, _ = model.transcribe(wav_path, language=lang, vad_filter=True)
        return _segments_to_vtt(seg_list)

    return run_blocking(_work, timeout=float(config.WHISPER_TIMEOUT))


def transcribe_to_sidecar(video_path: str, *, language: str = "en") -> dict[str, Any]:
    """ffmpeg 抽 16k 单声道 wav → Whisper → 写入同目录 sidecar vtt。"""
    lang = (language or "en").strip().lower()
    out_path = _sidecar_path(video_path, lang)
    with tempfile.TemporaryDirectory(prefix="mini_whisper_") as tmp:
        wav = os.path.join(tmp, "audio.wav")
        code, _, err = run_subprocess_safe(
            [config.FFMPEG_PATH, "-loglevel", "error", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", wav],
            timeout=float(config.FFMPEG_TIMEOUT))
        if code != 0:
            raise WhisperError(f"提取音频失败: {err.strip() or code}")
        vtt = _whisper_transcribe(wav, lang)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(vtt)

    return {
        "path": out_path,
        "remote_name": os.path.basename(out_path),
        "language": lang,
        "source": "whisper",
    }
