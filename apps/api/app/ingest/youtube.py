"""YouTube transcript ingestion (no media download). Shared by both source roles."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

from app.errors import ApiError
from app.ingest.material import Material
from app.models import SourceRole

ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
PATH_RE = re.compile(r"^/(?:shorts|embed|live)/([A-Za-z0-9_-]{11})/?$")
CACHE_TTL_S = 24 * 3600
MAX_VIDEO_SECONDS = 2 * 3600 + 15 * 60  # "~2 h" with a little slack


class TranscriptUnavailable(Exception):
    """Raised when the transcript cannot be read."""


def extract_video_id(url: str) -> str:
    """Return the 11-char video id or raise INVALID_URL. Never fetches the URL."""
    raw = (url or "").strip()
    if not raw:
        raise ApiError("INVALID_URL", 400)
    if "://" not in raw:
        raw = "https://" + raw
    try:
        parsed = urlparse(raw)
        port = parsed.port
    except ValueError as exc:
        raise ApiError("INVALID_URL", 400) from exc
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme not in ("http", "https")
        or host not in ALLOWED_HOSTS
        or port not in (None, 80, 443)
        or parsed.username
        or parsed.password
    ):
        raise ApiError("INVALID_URL", 400)

    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/")[0]
    elif parsed.path in ("/watch", "/watch/"):
        candidate = (parse_qs(parsed.query).get("v") or [""])[0]
    else:
        match = PATH_RE.match(parsed.path)
        candidate = match.group(1) if match else ""
    if not VIDEO_ID_RE.match(candidate):
        raise ApiError("INVALID_URL", 400)
    return candidate


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def _cache_path(cache_dir: Path, video_id: str) -> Path:
    return cache_dir / f"{video_id}.json"


def fetch_transcript(video_id: str, cache_dir: Path | None = None) -> list[tuple[int, str]]:
    """Fetch transcript snippets with youtube-transcript-api v1.x, cached for 24 h."""
    if cache_dir is not None:
        path = _cache_path(cache_dir, video_id)
        if path.exists() and time.time() - path.stat().st_mtime < CACHE_TTL_S:
            data = json.loads(path.read_text("utf-8"))
            return [(int(ts), str(text)) for ts, text in data]
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        ytt = YouTubeTranscriptApi()
        snippets = ytt.fetch(video_id, languages=["pt", "pt-BR", "en"])
        result = [(int(s.start), s.text.replace("\n", " ").strip()) for s in snippets]
    except Exception as exc:  # noqa: BLE001 - any failure means "unavailable"
        raise TranscriptUnavailable(type(exc).__name__) from exc
    result = [(ts, text) for ts, text in result if text]
    if not result:
        raise TranscriptUnavailable("empty")
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        _cache_path(cache_dir, video_id).write_text(json.dumps(result), "utf-8")
    return result


def fetch_oembed(video_id: str) -> tuple[str | None, str | None]:
    """Read public title/author metadata. Only ever calls the fixed oEmbed endpoint."""
    try:
        resp = httpx.get(
            "https://www.youtube.com/oembed",
            params={"url": canonical_url(video_id), "format": "json"},
            timeout=8.0,
        )
        if resp.status_code != 200:
            return None, None
        data = resp.json()
        return data.get("title"), data.get("author_name")
    except Exception:  # noqa: BLE001
        return None, None


def ingest_youtube(video_id: str, role: SourceRole, cache_dir: Path | None) -> Material:
    """Blocking ingestion of a YouTube source (call from a thread)."""
    code = "TRANSCRIPT_UNAVAILABLE" if role == "primaria" else "CONFRONTO_TRANSCRIPT_UNAVAILABLE"
    try:
        snippets = fetch_transcript(video_id, cache_dir)
    except TranscriptUnavailable as exc:
        raise ApiError(code, 422) from exc
    if snippets and snippets[-1][0] > MAX_VIDEO_SECONDS:
        raise ApiError(
            "INPUT_TOO_LONG",
            413,
            "Esse vídeo é longo demais. Use vídeos de até 2 horas ou cole um trecho do texto.",
        )
    title, author = fetch_oembed(video_id)
    return Material(
        role=role,
        kind="youtube",
        segments=[(ts, text) for ts, text in snippets],
        title=title,
        author=author,
        url=canonical_url(video_id),
        video_id=video_id,
    )
