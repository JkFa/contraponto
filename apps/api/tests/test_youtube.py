from __future__ import annotations

import pytest

from app.errors import ApiError
from app.ingest import youtube


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
        "http://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?si=abc",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "www.youtube.com/watch?v=dQw4w9WgXcQ",
    ],
)
def test_valid_urls(url: str) -> None:
    assert youtube.extract_video_id(url) == "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.evil.com/watch?v=dQw4w9WgXcQ",
        "https://evil.com/?u=https://youtu.be/dQw4w9WgXcQ",
        "file:///etc/passwd",
        "http://169.254.169.254/latest/meta-data",
        "https://user:pw@youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com:8080/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=short",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ/../../x",
        "javascript:alert(1)",
        "",
        "https://www.youtube.com/channel/abc",
    ],
)
def test_invalid_urls(url: str) -> None:
    with pytest.raises(ApiError) as exc:
        youtube.extract_video_id(url)
    assert exc.value.code == "INVALID_URL"
    assert exc.value.status == 400


@pytest.mark.parametrize(
    ("role", "code"),
    [("primaria", "TRANSCRIPT_UNAVAILABLE"), ("confronto", "CONFRONTO_TRANSCRIPT_UNAVAILABLE")],
)
def test_transcript_failure_code_per_role(monkeypatch, role: str, code: str) -> None:
    def boom(video_id, cache_dir=None):
        raise youtube.TranscriptUnavailable("blocked")

    monkeypatch.setattr(youtube, "fetch_transcript", boom)
    with pytest.raises(ApiError) as exc:
        youtube.ingest_youtube("dQw4w9WgXcQ", role, None)
    assert exc.value.code == code


def test_ingest_success_uses_oembed_and_formats_ts(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        youtube, "fetch_transcript", lambda vid, cache_dir=None: [(0, "olá"), (75, "mundo")]
    )
    monkeypatch.setattr(youtube, "fetch_oembed", lambda vid: ("Título", "Canal"))
    mat = youtube.ingest_youtube("dQw4w9WgXcQ", "primaria", tmp_path)
    assert mat.title == "Título" and mat.author == "Canal"
    assert mat.has_timestamps
    assert mat.formatted() == "[00:00] olá\n[01:15] mundo"
    assert mat.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_transcript_cache(monkeypatch, tmp_path) -> None:
    calls = {"n": 0}

    class FakeSnippet:
        def __init__(self, start, text):
            self.start, self.text = start, text

    class FakeApi:
        def fetch(self, vid, languages):
            calls["n"] += 1
            return [FakeSnippet(1.5, "linha\num")]

    import youtube_transcript_api

    monkeypatch.setattr(youtube_transcript_api, "YouTubeTranscriptApi", FakeApi)
    assert youtube.fetch_transcript("dQw4w9WgXcQ", tmp_path) == [(1, "linha um")]
    assert youtube.fetch_transcript("dQw4w9WgXcQ", tmp_path) == [(1, "linha um")]
    assert calls["n"] == 1


def test_too_long_video(monkeypatch) -> None:
    monkeypatch.setattr(
        youtube, "fetch_transcript", lambda vid, cache_dir=None: [(0, "a"), (3 * 3600, "b")]
    )
    with pytest.raises(ApiError) as exc:
        youtube.ingest_youtube("dQw4w9WgXcQ", "primaria", None)
    assert exc.value.code == "INPUT_TOO_LONG"
