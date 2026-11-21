"""Concatenate turns with natural pauses, normalize loudness and export MP3 (docs/04 §6)."""

from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass
from pathlib import Path

from app.models import Turn


class MixError(Exception):
    pass


@dataclass
class MixResult:
    path: Path
    duration_s: float
    bytes: int


async def _run(*args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise MixError(err.decode(errors="ignore")[-400:])
    return out.decode(errors="ignore")


def pause_ms(prev: Turn, nxt: Turn, rng: random.Random) -> int:
    """250–400 ms; longer after questions/transitions and when the quoted source changes."""
    long = prev.kind in ("pergunta", "transicao") or (
        prev.kind in ("citacao", "confronto")
        and nxt.kind in ("citacao", "confronto")
        and prev.role != nxt.role
    )
    return rng.randint(340, 400) if long else rng.randint(250, 320)


async def probe_duration(path: Path) -> float:
    out = await _run(
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)
    )
    return float(json.loads(out)["format"]["duration"])


async def mix_episode(
    turn_files: list[Path],
    turns: list[Turn],
    work_dir: Path,
    out_path: Path,
    seed: str,
    tags: dict[str, str],
) -> MixResult:
    if not turn_files or len(turn_files) != len(turns):
        raise MixError("turn/audio mismatch")
    rng = random.Random(seed)
    work_dir.mkdir(parents=True, exist_ok=True)

    pieces: list[Path] = []
    for i, src in enumerate(turn_files):
        wav = work_dir / f"n{i:03d}.wav"
        await _run(
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-ar",
            "44100",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(wav),
        )
        pieces.append(wav)
        if i < len(turn_files) - 1:
            ms = pause_ms(turns[i], turns[i + 1], rng)
            sil = work_dir / f"s{i:03d}.wav"
            await _run(
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=mono",
                "-t",
                f"{ms / 1000:.3f}",
                "-c:a",
                "pcm_s16le",
                str(sil),
            )
            pieces.append(sil)

    listing = work_dir / "concat.txt"
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in pieces), "utf-8")
    meta: list[str] = []
    for key, value in tags.items():
        meta += ["-metadata", f"{key}={value}"]
    await _run(
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(listing),
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar",
        "44100",
        "-ac",
        "1",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "128k",
        "-id3v2_version",
        "3",
        *meta,
        str(out_path),
    )
    for p in [*pieces, listing]:
        p.unlink(missing_ok=True)
    duration = await probe_duration(out_path)
    return MixResult(out_path, round(duration, 2), out_path.stat().st_size)
