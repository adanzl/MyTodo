"""聊天 TTS 音频 Redis 缓存（仅复用已完整生成的音频）。"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

import core.db.rds_mgr as rds_mgr

META_VERSION = 1
CACHE_TTL_SECONDS = 7 * 24 * 3600


def _text_digest(text: str) -> str:
    normalized = (text or "").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _model_for_role(role: str, model: Optional[str] = None) -> str:
    if model:
        return model
    from core.tts.tts_client import DEFAULT_MODEL, MODEL_MAP

    return MODEL_MAP.get(role, DEFAULT_MODEL)


def build_keys(
    msg_id: str,
    text: str,
    role: str,
    speed: float,
    model: Optional[str] = None,
) -> tuple[str, str, str]:
    """返回 (audio_key, meta_key, text_hash)。"""
    text_hash = _text_digest(text)
    model_name = _model_for_role(role, model)
    speed_key = f"{float(speed):.2f}"
    base = f"tts:v1:{msg_id}:{text_hash}:{role}:{speed_key}:{model_name}"
    return f"{base}:audio", f"{base}:meta", text_hash


def _read_meta(meta_key: str) -> Optional[dict[str, Any]]:
    if not rds_mgr.exists(meta_key):
        return None
    raw = rds_mgr.get_str(meta_key)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def get_complete_audio(
    msg_id: str,
    text: str,
    role: str,
    speed: float,
    model: Optional[str] = None,
) -> Optional[bytes]:
    audio_key, meta_key, text_hash = build_keys(msg_id, text, role, speed, model)
    meta = _read_meta(meta_key)
    if not meta or not meta.get("complete"):
        return None
    if meta.get("text_hash") != text_hash:
        return None
    if not rds_mgr.exists(audio_key):
        return None
    data = rds_mgr.get(audio_key)
    if not data:
        return None
    return data


def begin_session(
    msg_id: str,
    text: str,
    role: str,
    speed: float,
    model: Optional[str] = None,
) -> dict[str, str]:
    """开始一次新的合成：清除旧音频并标记 meta 为未完成。"""
    audio_key, meta_key, text_hash = build_keys(msg_id, text, role, speed, model)
    model_name = _model_for_role(role, model)
    # 音频本体也必须带 TTL；否则 meta 过期后 Redis 会永久遗留大块音频。
    rds_mgr.setex(audio_key, CACHE_TTL_SECONDS, b"")
    meta = {
        "v": META_VERSION,
        "complete": False,
        "text_hash": text_hash,
        "role": role,
        "speed": float(speed),
        "model": model_name,
    }
    rds_mgr.setex(meta_key, CACHE_TTL_SECONDS, json.dumps(meta, ensure_ascii=False))
    return {
        "audio_key": audio_key,
        "meta_key": meta_key,
        "text_hash": text_hash,
    }


def append_audio(session: dict[str, str], chunk: bytes) -> None:
    if not session or not chunk:
        return
    rds_mgr.append_value(session["audio_key"], chunk)


def finalize_session(session: Optional[dict[str, str]]) -> None:
    if not session:
        return
    meta = _read_meta(session["meta_key"]) or {}
    meta["complete"] = True
    meta["v"] = META_VERSION
    rds_mgr.setex(session["meta_key"], CACHE_TTL_SECONDS, json.dumps(meta, ensure_ascii=False))


def abort_session(session: Optional[dict[str, str]]) -> None:
    if not session:
        return
    rds_mgr.setex(session["audio_key"], CACHE_TTL_SECONDS, b"")
    meta = _read_meta(session["meta_key"]) or {}
    meta["complete"] = False
    meta["v"] = META_VERSION
    rds_mgr.setex(session["meta_key"], CACHE_TTL_SECONDS, json.dumps(meta, ensure_ascii=False))
