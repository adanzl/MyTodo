"""Device abstraction with minimal unified interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any


class DeviceBase(ABC):
    """Minimal device base class exposing play/stop/status."""

    def __init__(self, name: str = "") -> None:
        self.name = name or self.__class__.__name__

    # ---------------- Abstract unified interface ----------------
    @abstractmethod
    def play(self, source: str, **kwargs) -> Dict[str, Any]:
        """Start playing the given source (file/URL/track)."""

    @abstractmethod
    def stop(self) -> Dict[str, Any]:
        """Stop playback."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return current status dict (e.g., {state:'playing', position:..})."""

    @abstractmethod
    def get_volume(self) -> int | None:
        """Return current volume 0-100, None if unsupported."""

    @abstractmethod
    def set_volume(self, volume: int) -> bool:
        """Set volume level 0-100. Return True if accepted."""
