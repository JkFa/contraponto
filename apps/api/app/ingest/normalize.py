"""Cleaning, token estimation and chunking of ingested materials."""

from __future__ import annotations

import re

from app.ingest.material import Material

NOISE_RE = re.compile(
    r"\[(?:m[uú]sica|music|aplausos|applause|risos|laughter|risadas|inaud[ií]vel|"
    r"sil[eê]ncio|__)\]|♪+",
    re.IGNORECASE,
)
CHARS_PER_TOKEN = 3.6
CHUNK_TOKENS = 12_000


def clean_text(text: str) -> str:
    text = NOISE_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _dedupe_overlap(prev: str, cur: str) -> str:
    """Auto captions often repeat the tail of the previous line; drop that overlap."""
    if not prev or not cur:
        return cur
    if cur == prev:
        return ""
    prev_words = prev.split()
    cur_words = cur.split()
    max_k = min(len(prev_words), len(cur_words) - 1)
    for k in range(max_k, 2, -1):
        if [w.lower() for w in prev_words[-k:]] == [w.lower() for w in cur_words[:k]]:
            return " ".join(cur_words[k:])
    return cur


def normalize(material: Material) -> Material:
    """Return a cleaned copy of the material (noise markers, repeats, whitespace)."""
    cleaned: list[tuple[int | None, str]] = []
    prev_raw = ""
    for ts, text in material.segments:
        raw = clean_text(text)
        text = _dedupe_overlap(prev_raw, raw)
        if raw:
            prev_raw = raw
        if not text:
            continue
        cleaned.append((ts, text))
    material.segments = cleaned
    return material


def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


def chunk_segments(
    segments: list[tuple[int | None, str]], max_tokens: int = CHUNK_TOKENS
) -> list[list[tuple[int | None, str]]]:
    """Split segments into chunks of at most ~max_tokens (keeping timestamps)."""
    max_chars = int(max_tokens * CHARS_PER_TOKEN)
    chunks: list[list[tuple[int | None, str]]] = []
    current: list[tuple[int | None, str]] = []
    size = 0
    for seg in segments:
        seg_len = len(seg[1]) + 10
        if current and size + seg_len > max_chars:
            chunks.append(current)
            current, size = [], 0
        current.append(seg)
        size += seg_len
    if current:
        chunks.append(current)
    return chunks
