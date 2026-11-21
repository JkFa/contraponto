"""Mock TTS: a soft tone per turn (duration ∝ words), generated with FFmpeg."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.tts.base import TTSError, Voice


class MockTTS:
    name = "mock"

    def __init__(self, seconds_per_word: float = 0.05, delay_s: float = 0.0) -> None:
        self.seconds_per_word = seconds_per_word
        self.delay_s = delay_s

    async def synthesize(self, text: str, voice: Voice, out_path: Path) -> Path:
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        path = out_path.with_suffix(".wav")
        duration = max(0.4, min(6.0, len(text.split()) * self.seconds_per_word))
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={voice.tone_hz}:duration={duration:.2f}",
            "-af",
            f"volume=0.3,afade=t=in:d=0.05,afade=t=out:st={max(0.0, duration - 0.1):.2f}:d=0.1",
            "-ar",
            "44100",
            "-ac",
            "1",
            str(path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        if proc.returncode != 0:
            raise TTSError(err.decode(errors="ignore")[-200:])
        return path
