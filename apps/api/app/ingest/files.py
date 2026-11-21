"""Text and file ingestion (.txt, .srt, .pdf). Shared by both source roles."""

from __future__ import annotations

import io
import re

from app.errors import ApiError
from app.ingest.material import Material
from app.models import SourceRole

MAX_TEXT_CHARS = 60_000
MAX_FILE_BYTES = 5 * 1024 * 1024
ALLOWED_EXT = (".txt", ".srt", ".pdf")
SRT_TIME_RE = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->")


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _paragraphs(text: str) -> list[tuple[int | None, str]]:
    blocks = [re.sub(r"\s+", " ", b).strip() for b in re.split(r"\n\s*\n", text)]
    return [(None, b) for b in blocks if b]


def parse_srt(text: str) -> list[tuple[int | None, str]]:
    segments: list[tuple[int | None, str]] = []
    for block in re.split(r"\r?\n\s*\r?\n", text.strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        start: int | None = None
        body: list[str] = []
        for line in lines:
            match = SRT_TIME_RE.search(line)
            if match and start is None:
                h, m, s, _ = (int(g) for g in match.groups())
                start = h * 3600 + m * 60 + s
            elif line.isdigit() and start is None and not body:
                continue
            else:
                body.append(re.sub(r"<[^>]+>", "", line))
        content = " ".join(body).strip()
        if content:
            segments.append((start, content))
    return segments


def parse_pdf(data: bytes) -> list[tuple[int | None, str]]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # noqa: BLE001
        raise ApiError("FILE_UNSUPPORTED", 422) from exc
    text = "\n\n".join(pages)
    if len(re.sub(r"\s", "", text)) < 40:
        raise ApiError("PDF_NO_TEXT", 422)
    return _paragraphs(text)


def check_text_length(text: str) -> None:
    if len(text) > MAX_TEXT_CHARS:
        raise ApiError("INPUT_TOO_LONG", 413)


def ingest_text(text: str, role: SourceRole) -> Material:
    text = text.strip()
    check_text_length(text)
    return Material(role=role, kind="text", segments=_paragraphs(text), title=None)


def ingest_file(filename: str, data: bytes, role: SourceRole) -> Material:
    name = (filename or "").lower().strip()
    if len(data) > MAX_FILE_BYTES:
        raise ApiError("INPUT_TOO_LONG", 413, "O arquivo passa de 5 MB. Envie um arquivo menor.")
    ext = next((e for e in ALLOWED_EXT if name.endswith(e)), None)
    if ext is None:
        raise ApiError("FILE_UNSUPPORTED", 422)
    if ext == ".pdf":
        if not data.startswith(b"%PDF"):
            raise ApiError("FILE_UNSUPPORTED", 422)
        segments = parse_pdf(data)
    else:
        if b"\x00" in data[:4096]:
            raise ApiError("FILE_UNSUPPORTED", 422)
        text = _decode(data)
        segments = parse_srt(text) if ext == ".srt" else _paragraphs(text)
    if not segments:
        raise ApiError("FILE_UNSUPPORTED", 422)
    total = sum(len(t) for _, t in segments)
    if total > MAX_TEXT_CHARS * 2.5:  # a 2 h transcript is ~120-150k chars
        raise ApiError("INPUT_TOO_LONG", 413)
    if ext != ".srt" and total > MAX_TEXT_CHARS:
        raise ApiError("INPUT_TOO_LONG", 413)
    title = filename.rsplit("/", 1)[-1][:120] if filename else None
    return Material(role=role, kind="file", segments=segments, title=title)
