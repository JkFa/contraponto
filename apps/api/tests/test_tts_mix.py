from __future__ import annotations

import asyncio
import re
import subprocess

from app.mix import mix_episode, pause_ms
from app.models import Turn
from app.tts.base import Voice
from app.tts.mock import MockTTS
from app.tts.prepare import number_to_words, tts_prepare


def test_number_to_words() -> None:
    assert number_to_words(0) == "zero"
    assert number_to_words(21) == "vinte e um"
    assert number_to_words(100) == "cem"
    assert number_to_words(101) == "cento e um"
    assert number_to_words(1000) == "mil"
    assert number_to_words(2026) == "dois mil e vinte e seis"
    assert number_to_words(1_500_000) == "um milhão quinhentos mil"
    assert number_to_words(2_000_000) == "dois milhões"


def test_tts_prepare() -> None:
    assert tts_prepare("Subiu **30%** em 2020") == "Subiu trinta por cento em 2020"
    assert tts_prepare("Custa R$ 10") == "Custa dez reais"
    assert tts_prepare("R$ 1,50 cada") == "um real e cinquenta centavos cada"
    assert tts_prepare("A IA e os EUA") == "A I A e os É U A"
    assert tts_prepare("taxa de 2,5%") == "taxa de dois vírgula cinco por cento"


def test_pauses_are_in_range_and_longer_after_questions() -> None:
    import random

    rng = random.Random("x")
    q = Turn(speaker="HOST_1", text="?", kind="pergunta")
    c = Turn(speaker="HOST_2", text="ok", kind="contexto")
    for _ in range(50):
        assert 340 <= pause_ms(q, c, rng) <= 400
        assert 250 <= pause_ms(c, q, rng) <= 320


def test_mix_produces_normalized_mp3(tmp_path) -> None:
    turns = [
        Turn(speaker="HOST_1", text=" ".join(["palavra"] * 60), kind="contexto"),
        Turn(speaker="HOST_2", text=" ".join(["palavra"] * 60), kind="pergunta"),
        Turn(speaker="HOST_1", text=" ".join(["palavra"] * 60), kind="opiniao"),
    ]
    tts = MockTTS()

    async def go():
        files = [
            await tts.synthesize(t.text, Voice("x", tone_hz=220 + 110 * i), tmp_path / f"t{i}")
            for i, t in enumerate(turns)
        ]
        return await mix_episode(
            files,
            turns,
            tmp_path / "w",
            tmp_path / "ep.mp3",
            "seed",
            {"title": "Teste", "artist": "Contraponto (vozes sintéticas)"},
        )

    result = asyncio.run(go())
    assert result.path.exists() and result.bytes > 0
    assert result.duration_s > 8
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,sample_rate,channels,bit_rate:format_tags=artist",
            "-of",
            "default=nw=1",
            str(result.path),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "codec_name=mp3" in probe and "sample_rate=44100" in probe and "channels=1" in probe
    assert "Contraponto (vozes sintéticas)" in probe
    ebur = subprocess.run(
        ["ffmpeg", "-nostats", "-i", str(result.path), "-af", "ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
    ).stderr
    integrated = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", ebur)[-1])
    assert -18 <= integrated <= -14, integrated
