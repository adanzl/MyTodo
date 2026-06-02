"""Whisper 本地语音识别，生成 sidecar 字幕。"""

from __future__ import annotations

import os
import tempfile
import time
from typing import Any, Iterable

from core.config import app_logger, config
from core.tools.async_util import run_blocking
from core.utils import run_subprocess_safe

try:
    from faster_whisper import WhisperModel  # type: ignore[import-untyped]
except ImportError:
    WhisperModel = None  # type: ignore[misc, assignment]

log = app_logger

_ZH_LANGS = frozenset({"zh", "chs", "cht", "chi", "zho"})
_whisper_model: Any = None


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


def _whisper_transcribe_sync(wav_path: str, language: str) -> str:
    """在后台线程内同步执行 Whisper（勿在 gevent worker 主线程直接调用）。"""
    global _whisper_model
    if WhisperModel is None:
        raise WhisperError("未安装 faster-whisper，请执行: pip install faster-whisper")
    model_dir = (config.WHISPER_MODEL_DIR or "").strip()
    if not model_dir or not os.path.isdir(model_dir):
        raise WhisperError("请配置有效的 WHISPER_MODEL_DIR（faster_whisper.download_model 输出目录）")
    log.info(
        "[SUBTITLE] whisper transcribe start model=%s language=%s wav=%s",
        model_dir, language, wav_path,
    )
    t0 = time.monotonic()
    if _whisper_model is None:
        _whisper_model = WhisperModel(
            model_dir,
            device=(config.WHISPER_DEVICE or "cpu").strip(),
            compute_type=(config.WHISPER_COMPUTE_TYPE or "int8").strip(),
        )
    model = _whisper_model
    lang = (language or "en").strip() or None
    seg_list, info = model.transcribe(wav_path, language=lang, vad_filter=True)
    vtt = _segments_to_vtt(seg_list)
    elapsed = time.monotonic() - t0
    log.info(
        "[SUBTITLE] whisper transcribe done language=%s duration=%.1fs vtt_bytes=%d detected_lang=%s",
        language,
        elapsed,
        len(vtt.encode("utf-8")),
        getattr(info, "language", None),
    )
    return vtt


def transcribe_to_sidecar(video_path: str, *, language: str = "en") -> dict[str, Any]:
    """ffmpeg 抽 16k 单声道 wav → Whisper → 写入同目录 sidecar vtt（整段在后台线程执行）。"""
    lang = (language or "en").strip().lower()
    out_path = _sidecar_path(video_path, lang)
    wait = float(config.WHISPER_TIMEOUT) + float(config.FFMPEG_TIMEOUT) + 60.0

    def _work() -> dict[str, Any]:
        log.info(
            "[SUBTITLE] whisper recognize start video=%s language=%s out=%s",
            video_path,
            lang,
            out_path,
        )
        t0 = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="mini_whisper_") as tmp:
            wav = os.path.join(tmp, "audio.wav")
            log.info("[SUBTITLE] whisper extract audio video=%s", video_path)
            code, _, err = run_subprocess_safe(
                [
                    config.FFMPEG_PATH, "-loglevel", "error", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000",
                    wav
                ],
                timeout=float(config.FFMPEG_TIMEOUT),
            )
            if code != 0:
                raise WhisperError(f"提取音频失败: {err.strip() or code}")
            log.info("[SUBTITLE] whisper extract audio ok wav=%s", wav)
            vtt = _whisper_transcribe_sync(wav, lang)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(vtt)
        log.info(
            "[SUBTITLE] whisper recognize done video=%s out=%s elapsed=%.1fs",
            video_path,
            out_path,
            time.monotonic() - t0,
        )
        return {
            "path": out_path,
            "remote_name": os.path.basename(out_path),
            "language": lang,
            "source": "whisper",
        }

    return run_blocking(_work, timeout=wait)
