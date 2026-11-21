"""In-memory representation of an ingested source."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models import Source, SourceRole


def format_ts(seconds: int) -> str:
    """Format seconds as mm:ss or h:mm:ss."""
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_ts(value: str) -> int | None:
    """Parse mm:ss or h:mm:ss into seconds."""
    try:
        parts = [int(p) for p in value.strip().split(":")]
    except (ValueError, AttributeError):
        return None
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return None


@dataclass
class Material:
    """A source after ingestion: segments with optional start times (seconds)."""

    role: SourceRole
    kind: str  # youtube | text | file
    segments: list[tuple[int | None, str]] = field(default_factory=list)
    title: str | None = None
    author: str | None = None
    url: str | None = None
    video_id: str | None = None

    @property
    def has_timestamps(self) -> bool:
        return any(ts is not None for ts, _ in self.segments)

    def plain(self) -> str:
        return " ".join(text for _, text in self.segments)

    def formatted(self) -> str:
        if not self.has_timestamps:
            return "\n".join(text for _, text in self.segments)
        return "\n".join(
            f"[{format_ts(ts)}] {text}" if ts is not None else text for ts, text in self.segments
        )

    def to_source(self) -> Source:
        return Source(
            role=self.role,
            kind=self.kind,  # type: ignore[arg-type]
            title=self.title,
            author=self.author,
            url=self.url,
            has_timestamps=self.has_timestamps,
            char_count=len(self.plain()),
        )
