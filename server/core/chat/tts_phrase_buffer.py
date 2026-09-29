"""AI 流式回复 -> TTS 短句缓冲。"""

from __future__ import annotations

MAJOR_BREAKS = "。！？!?…\n"
MINOR_BREAKS = "，、；;：:"


class TtsPhraseBuffer:
    """将 AI 增量文本整理为适合 TTS 的短语。"""

    def __init__(
        self,
        *,
        first_soft_limit: int = 20,
        phrase_soft_limit: int = 72,
        hard_limit: int = 120,
    ) -> None:
        self._buf = ""
        self._full = ""
        self._first_sent = False
        self.first_soft_limit = first_soft_limit
        self.phrase_soft_limit = phrase_soft_limit
        self.hard_limit = hard_limit

    @property
    def full_text(self) -> str:
        return self._full

    def feed(self, chunk: str) -> list[str]:
        if not chunk:
            return []
        self._buf += chunk
        self._full += chunk
        out: list[str] = []
        while True:
            piece = self._take_one()
            if piece is None:
                break
            out.append(piece)
            self._first_sent = True
        return out

    def flush_rest(self) -> str | None:
        text = self._buf.strip()
        self._buf = ""
        return text or None

    def reset(self) -> None:
        self._buf = ""
        self._full = ""
        self._first_sent = False

    def _take_one(self) -> str | None:
        if not self._buf.strip():
            return None
        limit = self.first_soft_limit if not self._first_sent else self.phrase_soft_limit
        hard = min(self.hard_limit, max(limit * 2, limit + 20))

        for i, ch in enumerate(self._buf):
            if ch in MAJOR_BREAKS and i >= 1:
                piece = self._buf[: i + 1].strip()
                self._buf = self._buf[i + 1 :]
                return piece if piece else None

        if not self._first_sent:
            for i, ch in enumerate(self._buf):
                if ch in MINOR_BREAKS and i >= 4:
                    piece = self._buf[: i + 1].strip()
                    self._buf = self._buf[i + 1 :]
                    return piece if piece else None

        if len(self._buf) >= hard:
            cut = self._choose_hard_cut(self._buf, hard)
            piece = self._buf[:cut].strip()
            self._buf = self._buf[cut:]
            return piece if piece else None

        if len(self._buf) >= limit:
            cut = self._choose_soft_cut(self._buf, limit)
            if cut:
                piece = self._buf[:cut].strip()
                self._buf = self._buf[cut:]
                return piece if piece else None

        return None

    @staticmethod
    def _choose_soft_cut(text: str, limit: int) -> int | None:
        window = text[:limit]
        for i in range(len(window) - 1, -1, -1):
            if window[i] in MAJOR_BREAKS + MINOR_BREAKS:
                return i + 1
        return None

    @staticmethod
    def _choose_hard_cut(text: str, hard: int) -> int:
        window = text[:hard]
        for i in range(len(window) - 1, max(0, hard // 2), -1):
            if window[i] in MAJOR_BREAKS + MINOR_BREAKS + " ":
                return i + 1
        return hard
