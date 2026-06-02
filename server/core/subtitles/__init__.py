"""字幕：ASSRT 在线搜索、Whisper 本地识别。"""

from core.subtitles.assrt_client import AssrtClient, AssrtError, client as assrt_client
from core.subtitles.whisper_client import WhisperError, transcribe_to_sidecar

__all__ = [
    "AssrtClient",
    "AssrtError",
    "assrt_client",
    "WhisperError",
    "transcribe_to_sidecar",
]
