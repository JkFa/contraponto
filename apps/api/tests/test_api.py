from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.ingest import youtube
from app.main import create_app
from app.tts.mock import MockTTS
from tests.conftest import (
    CONFRONTO_TEXT,
    PRIMARY_TEXT,
    make_settings,
    manager_for,
    read_sse,
    wait_status,
)


def create(client: TestClient, **fields) -> dict:
    data = {"mode": "react", "duration_min": "3", **fields}
    files = data.pop("files", None)
    return client.post("/api/episodes", data=data, files=files)


def test_health(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body == {"ok": True, "version": "1.0.0", "llm": "mock", "tts": "mock"}


@pytest.mark.parametrize("with_confronto", [True, False])
def test_full_flow(client: TestClient, with_confronto: bool) -> None:
    fields = {"text": PRIMARY_TEXT}
    if with_confronto:
        fields["confronto_text"] = CONFRONTO_TEXT
    r = create(client, **fields)
    assert r.status_code == 202, r.text
    eid = r.json()["id"]
    assert r.json()["status"] == "created"

    events = read_sse(client, eid)
    assert events[-1] == ("done", {"status": "script_ready"})
    steps = [d.get("step") for e, d in events if e == "progress"]
    # The SSE may join mid-way, but the final state must be script_ready.
    ep = client.get(f"/api/episodes/{eid}").json()
    assert ep["status"] == "script_ready"
    assert len(ep["sources"]) == (2 if with_confronto else 1)
    script = ep["script"]
    roles = {v["evidence_role"] for v in script["verification"]}
    if with_confronto:
        assert "confronto" in roles
        assert any(t["kind"] == "confronto" for t in script["turns"])
    else:
        assert roles == {"interna"}
        assert not any(t["kind"] == "confronto" for t in script["turns"])
    assert steps is not None

    # edit a turn and a verification item, then render with the edited version
    script["turns"][0]["text"] = "Fala editada pela pessoa que revisa."
    script["verification"][0]["note"] = "Nota editada na revisão."
    r = client.put(f"/api/episodes/{eid}/script", json=script)
    assert r.status_code == 200, r.text
    assert r.json()["script"]["turns"][0]["text"] == "Fala editada pela pessoa que revisa."

    assert client.post(f"/api/episodes/{eid}/render", json={"music": False}).status_code == 202
    events = read_sse(client, eid)
    assert events[-1] == ("done", {"status": "ready"})
    ep = client.get(f"/api/episodes/{eid}").json()
    assert ep["status"] == "ready"
    assert ep["audio"]["duration_s"] > 0 and ep["audio"]["bytes"] > 0
    assert ep["share_url"] == f"http://testserver/s/{eid}"

    audio = client.get(f"/api/episodes/{eid}/audio.mp3")
    assert audio.status_code == 200 and audio.headers["content-type"] == "audio/mpeg"
    rng = client.get(f"/api/episodes/{eid}/audio.mp3", headers={"Range": "bytes=0-99"})
    assert rng.status_code == 206 and len(rng.content) == 100
    dl = client.get(f"/api/episodes/{eid}/audio.mp3?download=1")
    assert dl.headers["content-disposition"].startswith("attachment;")
    assert ".mp3" in dl.headers["content-disposition"]

    ver = client.get(f"/api/episodes/{eid}/verification.md").text
    assert "| Afirmação | Status | Nota |" in ver and "**Veredito:**" in ver
    assert "Nota editada na revisão." in ver
    md = client.get(f"/api/episodes/{eid}/script.md").text
    assert "Fala editada pela pessoa que revisa." in md and "vozes sintéticas" in md.lower()
    src = client.get(f"/api/episodes/{eid}/sources.md").text
    assert "Fonte primária" in src
    assert ("Material de confronto" in src) == with_confronto
    assert "exame de consistência interna" in src
    assert client.get(f"/api/episodes/{eid}/script.json").json()["verdict"]

    page = client.get(f"/s/{eid}")
    assert page.status_code == 200
    assert 'property="og:type" content="music.song"' in page.text
    assert "Vozes sintéticas" in page.text and "Veredito" in page.text
    assert "<script" not in page.text

    assert client.delete(f"/api/episodes/{eid}").status_code == 204
    assert client.get(f"/api/episodes/{eid}").status_code == 404
    assert client.get(f"/s/{eid}").status_code == 404


def test_progress_steps_cover_confronto(settings) -> None:
    """Subscribe before the job starts to see every step."""
    app = create_app(settings)
    with TestClient(app) as client:
        manager = app.state.jobs
        original = manager.start_scripting
        manager.start_scripting = lambda rec: None  # defer
        eid = create(client, text=PRIMARY_TEXT, confronto_text=CONFRONTO_TEXT).json()["id"]
        rec = manager.episodes[eid]
        manager.start_scripting = original

        async def collect():
            q = manager.subscribe(rec)
            manager.start_scripting(rec)
            out = []
            while True:
                ev, data = await q.get()
                out.append((ev, data))
                if ev in ("done", "error"):
                    return out

        events = client.portal.call(collect)
        steps = [d["step"] for e, d in events if e == "progress"]
        assert steps[:4] == [
            "Lendo a fonte primária",
            "Lendo o material de confronto",
            "Organizando o conteúdo",
            "Cruzando as informações",
        ]
        assert "Escrevendo o roteiro" in steps
        assert "Conferindo as citações e o veredito" in steps
        assert steps[-1] == "Roteiro pronto para revisão"


def test_progress_without_confronto_uses_internal_exam_step(settings) -> None:
    app = create_app(settings)
    with TestClient(app) as client:
        manager = app.state.jobs
        original = manager.start_scripting
        manager.start_scripting = lambda rec: None
        eid = create(client, text=PRIMARY_TEXT).json()["id"]
        rec = manager.episodes[eid]
        manager.start_scripting = original

        async def collect():
            q = manager.subscribe(rec)
            manager.start_scripting(rec)
            out = []
            while True:
                ev, data = await q.get()
                out.append(data.get("step"))
                if ev in ("done", "error"):
                    return out

        steps = client.portal.call(collect)
        assert "Lendo o material de confronto" not in steps
        assert "Examinando a consistência do material" in steps


# ---------- input validation ----------


@pytest.mark.parametrize("field", ["youtube_url", "confronto_youtube_url"])
@pytest.mark.parametrize(
    "url", ["https://evil.com/watch?v=dQw4w9WgXcQ", "file:///etc/passwd", "http://169.254.169.254/"]
)
def test_invalid_urls(client: TestClient, field: str, url: str) -> None:
    fields = {field: url}
    if field.startswith("confronto"):
        fields["text"] = PRIMARY_TEXT
    r = create(client, **fields)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_URL"


@pytest.mark.parametrize("field", ["text", "confronto_text"])
def test_text_too_long(client: TestClient, field: str) -> None:
    fields = {field: "a" * 60_001}
    if field == "confronto_text":
        fields["text"] = PRIMARY_TEXT
    r = create(client, **fields)
    assert r.status_code == 413 and r.json()["error"]["code"] == "INPUT_TOO_LONG"


def test_file_too_big_and_unsupported(client: TestClient) -> None:
    r = create(client, files={"file": ("a.txt", b"a" * (5 * 1024 * 1024 + 10), "text/plain")})
    assert r.status_code == 413
    r = create(client, files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 422 and r.json()["error"]["code"] == "FILE_UNSUPPORTED"
    r = create(
        client,
        text=PRIMARY_TEXT,
        files={"confronto_file": ("x.exe", b"MZ", "application/octet-stream")},
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "FILE_UNSUPPORTED"


def test_file_upload_as_both_sources(client: TestClient) -> None:
    srt = b"1\n00:00:05,000 --> 00:00:07,000\nO consumo de cafe cresceu muito no pais.\n"
    r = create(
        client,
        files={
            "file": ("fala.srt", srt, "application/x-subrip"),
            "confronto_file": ("dados.txt", CONFRONTO_TEXT.encode(), "text/plain"),
        },
    )
    assert r.status_code == 202, r.text
    ep = wait_status(client, r.json()["id"], {"script_ready", "failed"})
    assert ep["status"] == "script_ready", ep
    assert ep["sources"][0]["has_timestamps"] is True
    assert ep["sources"][0]["kind"] == "file" and ep["sources"][1]["role"] == "confronto"


def test_multiple_inputs(client: TestClient) -> None:
    r = create(
        client,
        text=PRIMARY_TEXT,
        confronto_text="a",
        confronto_youtube_url="https://youtu.be/dQw4w9WgXcQ",
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "MULTIPLE_CONFRONTO_INPUTS"
    r = create(client, text=PRIMARY_TEXT, youtube_url="https://youtu.be/dQw4w9WgXcQ")
    assert r.json()["error"]["code"] == "MULTIPLE_PRIMARY_INPUTS"
    r = create(client)
    assert r.json()["error"]["code"] == "MISSING_PRIMARY"


def test_critica_requires_thesis(client: TestClient) -> None:
    r = create(client, mode="critica", text=PRIMARY_TEXT)
    assert r.status_code == 422 and r.json()["error"]["code"] == "THESIS_REQUIRED"
    r = create(client, mode="critica", text=PRIMARY_TEXT, thesis="x" * 2001)
    assert r.status_code == 422
    r = create(client, mode="critica", text=PRIMARY_TEXT, thesis="- exagera\n- sem dados")
    assert r.status_code == 202


def test_bad_enum_values(client: TestClient) -> None:
    assert create(client, text="a", mode="outro").status_code == 422
    assert create(client, text="a", duration_min="7").status_code == 422
    assert create(client, text="a", tone="raivoso").status_code == 422


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("youtube_url", "TRANSCRIPT_UNAVAILABLE"),
        ("confronto_youtube_url", "CONFRONTO_TRANSCRIPT_UNAVAILABLE"),
    ],
)
def test_transcript_unavailable(client: TestClient, monkeypatch, field: str, code: str) -> None:
    def boom(video_id, cache_dir=None):
        raise youtube.TranscriptUnavailable("blocked")

    monkeypatch.setattr(youtube, "fetch_transcript", boom)
    fields = {field: "https://youtu.be/dQw4w9WgXcQ"}
    if field.startswith("confronto"):
        fields["text"] = PRIMARY_TEXT
    eid = create(client, **fields).json()["id"]
    events = read_sse(client, eid)
    assert events[-1][0] == "error" and events[-1][1]["code"] == code
    ep = client.get(f"/api/episodes/{eid}").json()
    assert ep["status"] == "failed" and ep["error"]["code"] == code


def test_youtube_source_ingested(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        youtube,
        "fetch_transcript",
        lambda vid, cache_dir=None: [
            (0, "O consumo de café cresceu muito."),
            (65, "Todo mundo bebe."),
        ],
    )
    monkeypatch.setattr(youtube, "fetch_oembed", lambda vid: ("Vídeo <b>X</b>", "Canal Y"))
    eid = create(client, youtube_url="https://youtu.be/dQw4w9WgXcQ").json()["id"]
    ep = wait_status(client, eid, {"script_ready", "failed"})
    assert ep["status"] == "script_ready"
    src = ep["sources"][0]
    assert src["title"] == "Vídeo <b>X</b>" and src["author"] == "Canal Y"
    assert src["has_timestamps"] is True
    quotes = [t for t in ep["script"]["turns"] if t["kind"] == "citacao"]
    assert all(t["source_ts"] for t in quotes)
    page = client.get(f"/s/{eid}").text
    assert "Vídeo &lt;b&gt;X&lt;/b&gt;" in page and "<b>X</b>" not in page


# ---------- state rules ----------


def test_render_and_edit_outside_script_ready(client: TestClient, settings) -> None:
    eid = create(client, text=PRIMARY_TEXT).json()["id"]
    ep = wait_status(client, eid, {"script_ready"})
    script = ep["script"]
    client.post(f"/api/episodes/{eid}/render")
    r = client.post(f"/api/episodes/{eid}/render")
    assert r.status_code == 409
    assert client.put(f"/api/episodes/{eid}/script", json=script).status_code == 409
    wait_status(client, eid, {"ready"})
    assert client.post(f"/api/episodes/{eid}/render").status_code == 409


def test_invalid_edit_rejected(client: TestClient) -> None:
    eid = create(client, text=PRIMARY_TEXT).json()["id"]
    script = wait_status(client, eid, {"script_ready"})["script"]
    bad = dict(script, verification=script["verification"][:2])
    r = client.put(f"/api/episodes/{eid}/script", json=bad)
    assert r.status_code == 422 and r.json()["error"]["code"] == "SCRIPT_INVALID"
    bad = dict(script, verdict="")
    assert client.put(f"/api/episodes/{eid}/script", json=bad).status_code == 422
    bad = dict(script, turns=[dict(script["turns"][0], text="x" * 601)])
    assert client.put(f"/api/episodes/{eid}/script", json=bad).status_code == 422


def test_regenerate(client: TestClient) -> None:
    eid = create(client, text=PRIMARY_TEXT, confronto_text=CONFRONTO_TEXT).json()["id"]
    wait_status(client, eid, {"script_ready"})
    r = client.post(f"/api/episodes/{eid}/regenerate", json={"instructions": "mais curto"})
    assert r.status_code == 202
    ep = wait_status(client, eid, {"script_ready"})
    assert ep["script"]["verification"]


def test_expired_episode(client: TestClient) -> None:
    eid = create(client, text=PRIMARY_TEXT).json()["id"]
    wait_status(client, eid, {"script_ready"})
    manager = client.app.state.jobs
    folder = manager.storage.episode_dir(eid)
    manager.episodes[eid].expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert manager.cleanup() == 1
    assert not folder.exists()
    r = client.get(f"/api/episodes/{eid}")
    assert r.status_code == 404 and r.json()["error"]["code"] == "EXPIRED"


def test_unknown_episode(client: TestClient) -> None:
    assert client.get("/api/episodes/nope").json()["error"]["code"] == "EXPIRED"


# ---------- security ----------


def test_byok_header_never_logged(client: TestClient, caplog) -> None:
    secret = "AIzaSy-SECRET-KEY-123456"
    caplog.set_level(logging.DEBUG)
    r = client.post(
        "/api/episodes",
        data={"mode": "react", "text": PRIMARY_TEXT, "duration_min": "3"},
        headers={"X-Gemini-Key": secret},
    )
    eid = r.json()["id"]
    wait_status(client, eid, {"script_ready"})
    assert secret not in caplog.text
    assert PRIMARY_TEXT[:30] not in caplog.text  # no user content in logs
    assert secret not in client.get(f"/api/episodes/{eid}").text


def test_cors(client: TestClient) -> None:
    ok = client.options(
        "/api/health",
        headers={"Origin": "https://jkfa.github.io", "Access-Control-Request-Method": "GET"},
    )
    assert ok.headers.get("access-control-allow-origin") == "https://jkfa.github.io"
    bad = client.options(
        "/api/health",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert bad.status_code == 400
    assert "access-control-allow-origin" not in bad.headers
    simple = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in simple.headers


def test_rate_limit(tmp_path) -> None:
    settings = make_settings(tmp_path, rate_limit_enabled=True, episodes_per_hour=3)
    with TestClient(create_app(settings)) as client:
        codes = [create(client, text=PRIMARY_TEXT).status_code for _ in range(4)]
        assert codes == [202, 202, 202, 429]
        r = create(client, text=PRIMARY_TEXT)
        assert r.json()["error"]["code"] == "RATE_LIMITED"


def test_concurrent_renders_respect_limit(tmp_path) -> None:
    settings = make_settings(tmp_path, max_concurrent_renders=2)
    manager = manager_for(settings, tts_factory=lambda s: MockTTS(delay_s=0.05))
    with TestClient(create_app(settings, jobs=manager)) as client:
        ids = [create(client, text=PRIMARY_TEXT).json()["id"] for _ in range(3)]
        for eid in ids:
            wait_status(client, eid, {"script_ready"})
        for eid in ids:
            assert client.post(f"/api/episodes/{eid}/render").status_code == 202
        for eid in ids:
            assert wait_status(client, eid, {"ready", "failed"}, timeout=60)["status"] == "ready"
        assert manager.peak_renders == 2


def test_llm_not_configured(tmp_path) -> None:
    settings = make_settings(tmp_path, mock_llm=False, llm_provider="gemini")
    with TestClient(create_app(settings)) as client:
        eid = create(client, text=PRIMARY_TEXT).json()["id"]
        ep = wait_status(client, eid, {"failed", "script_ready"})
        assert ep["error"]["code"] == "LLM_NOT_CONFIGURED"


def test_keepalive_constant() -> None:
    from app import main

    assert main.KEEPALIVE_S == 15.0
    assert asyncio is not None


def test_base_url_fallbacks(tmp_path) -> None:
    assert make_settings(tmp_path, public_base_url="").base_url == "http://localhost:8000"
    s = make_settings(tmp_path, public_base_url="", render_external_url="https://x.onrender.com/")
    assert s.base_url == "https://x.onrender.com"
    s = make_settings(
        tmp_path, public_base_url="https://api.example/", render_external_url="https://x"
    )
    assert s.base_url == "https://api.example"
