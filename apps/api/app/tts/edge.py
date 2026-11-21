"""Microsoft Edge Read Aloud voices via edge-tts (unofficial API)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.tts.base import TTSError, Voice


class EdgeTTS:
    name = "edge"

    def __init__(self, retries: int = 2) -> None:
        self.retries = retries

    async def synthesize(self, text: str, voice: Voice, out_path: Path) -> Path:
        import edge_tts

        path = out_path.with_suffix(".mp3")
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                comm = edge_tts.Communicate(text, voice.name, rate=voice.rate, pitch=voice.pitch)
                await comm.save(str(path))
                if path.exists() and path.stat().st_size > 0:
                    return path
                raise TTSError("empty audio")
            except Exception as exc:  # noqa: BLE001
                last = exc
                await asyncio.sleep(1.5 * (attempt + 1))
        raise TTSError(type(last).__name__ if last else "unknown")
