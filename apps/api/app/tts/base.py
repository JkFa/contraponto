"""TTS provider interface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class TTSError(Exception):
    pass


@dataclass(frozen=True)
class Voice:
    name: str
    rate: str = "+0%"
    pitch: str = "+0Hz"
    tone_hz: int = 220  # mock only


class TTSProvider(Protocol):
    name: str

    async def synthesize(self, text: str, voice: Voice, out_path: Path) -> Path:
        """Write audio for `text` and return the written file path."""
        ...
