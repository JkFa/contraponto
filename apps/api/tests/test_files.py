from __future__ import annotations

import io

import pytest

from app.errors import ApiError
from app.ingest import files
from app.ingest.material import Material, format_ts, parse_ts
from app.ingest.normalize import chunk_segments, estimate_tokens, normalize


def _text_pdf(text: str) -> bytes:
    """Build a minimal valid PDF with one text line (no external deps)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer << /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return out.getvalue()


def _blank_pdf() -> bytes:
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(612, 792)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def test_txt_utf8_and_latin1() -> None:
    m = files.ingest_file("a.txt", "Olá, ação!\n\nSegundo parágrafo.".encode(), "primaria")
    assert m.segments == [(None, "Olá, ação!"), (None, "Segundo parágrafo.")]
    m2 = files.ingest_file("b.TXT", "Coração".encode("latin-1"), "confronto")
    assert m2.plain() == "Coração" and m2.role == "confronto"


def test_srt_keeps_timestamps() -> None:
    srt = (
        "1\n00:00:01,000 --> 00:00:03,000\nPrimeira <i>fala</i>\n\n"
        "2\n00:01:05,500 --> 00:01:07,000\nSegunda\nlinha\n"
    )
    m = files.ingest_file("leg.srt", srt.encode(), "primaria")
    assert m.segments == [(1, "Primeira fala"), (65, "Segunda linha")]
    assert m.has_timestamps


@pytest.mark.parametrize("role", ["primaria", "confronto"])
def test_pdf_with_text(role: str) -> None:
    data = _text_pdf("Este documento afirma que o cafe faz bem a saude de todos os adultos.")
    m = files.ingest_file("doc.pdf", data, role)  # type: ignore[arg-type]
    assert "cafe faz bem" in m.plain()


@pytest.mark.parametrize("role", ["primaria", "confronto"])
def test_scanned_pdf(role: str) -> None:
    with pytest.raises(ApiError) as exc:
        files.ingest_file("scan.pdf", _blank_pdf(), role)  # type: ignore[arg-type]
    assert exc.value.code == "PDF_NO_TEXT"


@pytest.mark.parametrize(
    ("name", "data"),
    [("virus.exe", b"MZ..."), ("fake.pdf", b"not a pdf"), ("bin.txt", b"\x00\x01\x02")],
)
def test_unsupported(name: str, data: bytes) -> None:
    with pytest.raises(ApiError) as exc:
        files.ingest_file(name, data, "primaria")
    assert exc.value.code == "FILE_UNSUPPORTED"


def test_file_too_big() -> None:
    with pytest.raises(ApiError) as exc:
        files.ingest_file("a.txt", b"a" * (5 * 1024 * 1024 + 1), "primaria")
    assert exc.value.code == "INPUT_TOO_LONG" and exc.value.status == 413


def test_text_too_long() -> None:
    with pytest.raises(ApiError) as exc:
        files.ingest_text("a" * 60_001, "confronto")
    assert exc.value.code == "INPUT_TOO_LONG"


def test_normalize_removes_noise_and_overlap() -> None:
    m = Material(
        role="primaria",
        kind="youtube",
        segments=[
            (0, "[Música] olá   pessoal tudo bem"),
            (2, "pessoal tudo bem com vocês hoje"),
            (4, "pessoal tudo bem com vocês hoje"),
            (6, "[Aplausos]"),
        ],
    )
    normalize(m)
    assert m.segments == [(0, "olá pessoal tudo bem"), (2, "com vocês hoje")]


def test_chunking_and_tokens() -> None:
    segs = [(i, "x" * 1000) for i in range(100)]
    chunks = chunk_segments(segs, max_tokens=5000)
    assert len(chunks) > 1
    assert sum(len(c) for c in chunks) == 100
    assert estimate_tokens("a" * 36) == 10


def test_ts_helpers() -> None:
    assert format_ts(5) == "00:05"
    assert format_ts(3725) == "1:02:05"
    assert parse_ts("1:02:05") == 3725
    assert parse_ts("02:05") == 125
    assert parse_ts("x") is None
