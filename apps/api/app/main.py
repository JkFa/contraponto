"""FastAPI application: routes, CORS, rate limiting, error handling (docs/03-API.md)."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, Header, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import StreamingResponse

from app import __version__
from app.config import Settings, get_settings
from app.errors import ApiError
from app.exports import script_md, slugify, sources_md
from app.ingest.files import MAX_FILE_BYTES, check_text_length, ingest_file, ingest_text
from app.ingest.youtube import extract_video_id
from app.jobs import EpisodeRecord, JobManager, PendingInput
from app.models import Episode, RegenerateBody, RenderBody, Script
from app.script_service import ScriptError, validate_user_script
from app.share_page import render_not_found, render_share_page
from app.storage import Storage
from app.verification import render_verification_md

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("contraponto.api")

DURATIONS = {3, 5, 8, 12}
TONES = {"descontraido", "analitico", "provocativo"}
KEEPALIVE_S = 15.0


class RateLimiter:
    """Sliding-window limiter per (bucket, client)."""

    def __init__(self) -> None:
        self.hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(self, bucket: str, key: str, limit: int, window_s: float) -> None:
        now = time.monotonic()
        q = self.hits[(bucket, key)]
        while q and now - q[0] > window_s:
            q.popleft()
        if len(q) >= limit:
            raise ApiError("RATE_LIMITED", 429)
        q.append(now)


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def create_app(settings: Settings | None = None, jobs: JobManager | None = None) -> FastAPI:
    settings = settings or get_settings()
    storage = Storage(settings.data_dir)
    manager = jobs or JobManager(settings, storage)
    limiter = RateLimiter()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        task = asyncio.create_task(manager.cleanup_loop())
        yield
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    app = FastAPI(title="Contraponto API", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.jobs = manager
    app.state.limiter = limiter

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Gemini-Key", "Range", "Last-Event-ID"],
        expose_headers=["Content-Disposition", "Content-Range", "Accept-Ranges", "Content-Length"],
        max_age=600,
    )

    # ---------- errors ----------
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(exc.to_dict(), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [".".join(str(p) for p in e.get("loc", [])[1:]) for e in exc.errors()[:5]]
        err = ApiError("VALIDATION_ERROR", 422)
        body = err.to_dict()
        body["error"]["fields"] = fields  # type: ignore[assignment]
        return JSONResponse(body, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "EXPIRED" if exc.status_code == 404 else "INTERNAL"
        msg = None if exc.status_code == 404 else str(exc.detail)
        return JSONResponse(ApiError(code, exc.status_code, msg).to_dict(), exc.status_code)

    def limit(request: Request, create: bool = False) -> None:
        if not settings.rate_limit_enabled:
            return
        ip = client_ip(request)
        limiter.check("minute", ip, settings.rate_limit_per_minute, 60)
        if create:
            limiter.check("hour", ip, settings.episodes_per_hour, 3600)

    # ---------- routes ----------
    @app.get("/")
    async def root() -> dict[str, str]:
        return {"name": "Contraponto API", "health": "/api/health", "app": settings.frontend_url}

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "version": __version__,
            "llm": settings.llm_name,
            "tts": settings.tts_name,
        }

    @app.post("/api/episodes", status_code=202)
    async def create_episode(
        request: Request,
        mode: Annotated[str, Form()],
        youtube_url: Annotated[str | None, Form()] = None,
        text: Annotated[str | None, Form()] = None,
        file: Annotated[UploadFile | None, File()] = None,
        confronto_youtube_url: Annotated[str | None, Form()] = None,
        confronto_text: Annotated[str | None, Form()] = None,
        confronto_file: Annotated[UploadFile | None, File()] = None,
        thesis: Annotated[str | None, Form()] = None,
        focus_points: Annotated[str | None, Form()] = None,
        duration_min: Annotated[int, Form()] = 5,
        tone: Annotated[str, Form()] = "analitico",
        host1_name: Annotated[str | None, Form()] = None,
        host2_name: Annotated[str | None, Form()] = None,
        x_gemini_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, str]:
        limit(request, create=True)
        if mode not in ("critica", "react"):
            raise ApiError("VALIDATION_ERROR", 422)
        if duration_min not in DURATIONS or tone not in TONES:
            raise ApiError("VALIDATION_ERROR", 422)

        file_ok = file is not None and bool(file.filename)
        cfile_ok = confronto_file is not None and bool(confronto_file.filename)
        primary_fields = [_clean(youtube_url), _clean(text), file_ok or None]
        confronto_fields = [_clean(confronto_youtube_url), _clean(confronto_text), cfile_ok or None]
        n_primary = sum(1 for f in primary_fields if f)
        if n_primary == 0:
            raise ApiError("MISSING_PRIMARY", 422)
        if n_primary > 1:
            raise ApiError("MULTIPLE_PRIMARY_INPUTS", 422)
        if sum(1 for f in confronto_fields if f) > 1:
            raise ApiError("MULTIPLE_CONFRONTO_INPUTS", 422)

        thesis_v = _clean(thesis)
        if mode == "critica" and not thesis_v:
            raise ApiError("THESIS_REQUIRED", 422)
        if thesis_v and len(thesis_v) > 2000:
            raise ApiError("VALIDATION_ERROR", 422, "A tese pode ter até 2 000 caracteres.")
        focus_v = _clean(focus_points) if mode == "react" else None
        if focus_v and len(focus_v) > 2000:
            raise ApiError(
                "VALIDATION_ERROR", 422, "Os pontos de atenção podem ter até 2 000 caracteres."
            )

        async def read_upload(upload: UploadFile) -> bytes:
            data = await upload.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES:
                raise ApiError(
                    "INPUT_TOO_LONG", 413, "O arquivo passa de 5 MB. Envie um arquivo menor."
                )
            return data

        async def pending(
            role: str, url: str | None, txt: str | None, upload: UploadFile | None, has_file: bool
        ) -> PendingInput:
            if url:
                return PendingInput(role=role, video_id=extract_video_id(url))
            if txt:
                check_text_length(txt)
                return PendingInput(role=role, material=ingest_text(txt, role))  # type: ignore[arg-type]
            assert upload is not None and has_file
            data = await read_upload(upload)
            mat = await asyncio.to_thread(ingest_file, upload.filename or "", data, role)
            return PendingInput(role=role, material=mat)

        primary_in = await pending("primaria", _clean(youtube_url), _clean(text), file, file_ok)
        confronto_in = None
        if any(confronto_fields):
            confronto_in = await pending(
                "confronto",
                _clean(confronto_youtube_url),
                _clean(confronto_text),
                confronto_file,
                cfile_ok,
            )

        h1 = (_clean(host1_name) or "Davi")[:40]
        h2 = (_clean(host2_name) or "Lia")[:40]
        rec = manager.create(
            mode=mode,
            tone=tone,
            duration_min=duration_min,
            hosts=(h1, h2),
            thesis=thesis_v if mode == "critica" else None,
            focus_points=focus_v,
            primary_input=primary_in,
            confronto_input=confronto_in,
            gemini_key=_clean(x_gemini_key),
        )
        manager.start_scripting(rec)
        return {"id": rec.id, "status": "created"}

    @app.get("/api/episodes/{episode_id}", response_model=Episode)
    async def get_episode(episode_id: str) -> Episode:
        return manager.to_episode(manager.get(episode_id))

    @app.get("/api/episodes/{episode_id}/events")
    async def events(episode_id: str, request: Request) -> StreamingResponse:
        rec = manager.get(episode_id)

        async def stream() -> AsyncIterator[str]:
            queue = manager.subscribe(rec)
            try:
                event, data = manager.current_event(rec)
                yield _sse(event, data)
                if event in ("done", "error"):
                    return
                while True:
                    try:
                        event, data = await asyncio.wait_for(queue.get(), KEEPALIVE_S)
                    except TimeoutError:
                        if await request.is_disconnected():
                            return
                        yield ": keep-alive\n\n"
                        continue
                    yield _sse(event, data)
                    if event in ("done", "error"):
                        return
            finally:
                manager.unsubscribe(rec, queue)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.put("/api/episodes/{episode_id}/script", response_model=Episode)
    async def save_script(episode_id: str, request: Request) -> Episode:
        rec = manager.get(episode_id)
        if rec.status != "script_ready" or rec.primary is None:
            raise ApiError("INVALID_STATE", 409)
        try:
            payload = await request.json()
            script = Script.model_validate(payload)
        except (ValueError, ValidationError) as exc:
            raise ApiError("SCRIPT_INVALID", 422, _validation_message(exc)) from exc
        script.hosts.HOST_1, script.hosts.HOST_2 = rec.hosts
        try:
            rec.script = validate_user_script(script, rec.primary, rec.confronto)
        except ScriptError as exc:
            raise ApiError(
                "SCRIPT_INVALID", 422, f"O roteiro editado tem problemas: {exc.detail}"
            ) from exc
        return manager.to_episode(rec)

    @app.post("/api/episodes/{episode_id}/regenerate", status_code=202)
    async def regenerate(
        episode_id: str,
        request: Request,
        x_gemini_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, str]:
        limit(request)
        rec = manager.get(episode_id)
        body = await _optional_body(request, RegenerateBody)
        if _clean(x_gemini_key):
            rec.gemini_key = _clean(x_gemini_key)
        manager.start_regenerate(rec, body.instructions)
        return {"status": "scripting"}

    @app.post("/api/episodes/{episode_id}/render", status_code=202)
    async def render(episode_id: str, request: Request) -> dict[str, str]:
        limit(request)
        rec = manager.get(episode_id)
        await _optional_body(request, RenderBody)  # music: ignored, no CC0 track registered
        manager.start_render(rec)
        return {"status": "rendering"}

    @app.get("/api/episodes/{episode_id}/audio.mp3")
    async def audio(episode_id: str, download: int = 0) -> FileResponse:
        rec = manager.get(episode_id)
        path = manager.storage.audio_path(rec.id)
        if rec.status != "ready" or not path.exists():
            raise ApiError("NOT_READY", 409)
        if download:
            name = slugify(rec.script.title if rec.script else "episodio") + ".mp3"
            return FileResponse(path, media_type="audio/mpeg", filename=name)
        return FileResponse(path, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})

    def _with_script(episode_id: str) -> tuple[EpisodeRecord, Script]:
        rec = manager.get(episode_id)
        if rec.script is None:
            raise ApiError("NOT_READY", 409)
        return rec, rec.script

    def _md(content: str, filename: str) -> Response:
        return Response(
            content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/episodes/{episode_id}/script.md")
    async def get_script_md(episode_id: str) -> Response:
        rec, script = _with_script(episode_id)
        srcs = rec.sources
        return _md(script_md(script, srcs[0], srcs[1] if len(srcs) > 1 else None), "roteiro.md")

    @app.get("/api/episodes/{episode_id}/script.json")
    async def get_script_json(episode_id: str) -> Response:
        _, script = _with_script(episode_id)
        return Response(
            script.model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="roteiro.json"'},
        )

    @app.get("/api/episodes/{episode_id}/verification.md")
    async def get_verification_md(episode_id: str) -> Response:
        rec, script = _with_script(episode_id)
        srcs = rec.sources
        examined = srcs[0].title or srcs[0].url or "material enviado"
        conf = (srcs[1].title or srcs[1].url or "material de confronto") if len(srcs) > 1 else None
        return _md(render_verification_md(script, examined, conf), "verificacao.md")

    @app.get("/api/episodes/{episode_id}/sources.md")
    async def get_sources_md(episode_id: str) -> Response:
        rec = manager.get(episode_id)
        srcs = rec.sources
        content = sources_md(
            rec.script,
            srcs[0],
            srcs[1] if len(srcs) > 1 else None,
            rec.created_at.astimezone(UTC),
            llm=_llm_label(rec.llm_used or settings.llm_name, settings),
            tts=_tts_label(rec.tts_used or settings.tts_name),
        )
        return _md(content, "fontes.md")

    @app.delete("/api/episodes/{episode_id}", status_code=204)
    async def delete_episode(episode_id: str) -> Response:
        manager.get(episode_id)
        manager.delete(episode_id)
        return Response(status_code=204)

    @app.get("/s/{episode_id}", response_class=HTMLResponse)
    async def share(episode_id: str) -> HTMLResponse:
        try:
            rec = manager.get(episode_id)
        except ApiError:
            return HTMLResponse(render_not_found(settings.frontend_url), status_code=404)
        base = settings.public_base_url.rstrip("/")
        html = render_share_page(
            manager.to_episode(rec),
            audio_url=f"{base}/api/episodes/{rec.id}/audio.mp3",
            frontend_url=settings.frontend_url,
            page_url=f"{base}/s/{rec.id}",
        )
        return HTMLResponse(
            html,
            headers={
                "Content-Security-Policy": "default-src 'none'; "
                "style-src 'unsafe-inline'; media-src *; img-src *"
            },
        )

    return app


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _optional_body(request: Request, model: type[Any]) -> Any:
    raw = await request.body()
    if not raw.strip():
        return model()
    try:
        return model.model_validate_json(raw)
    except ValidationError as exc:
        raise ApiError("VALIDATION_ERROR", 422) from exc


def _validation_message(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        first = exc.errors()[0]
        loc = ".".join(str(p) for p in first["loc"])
        return f"O roteiro editado tem um campo inválido ({loc}): {first['msg']}."
    return "O roteiro enviado não é um JSON válido."


def _llm_label(name: str, settings: Settings) -> str:
    return {
        "gemini": f"Google Gemini ({settings.gemini_model})",
        "groq": f"Groq ({settings.groq_model})",
        "mock": "simulado (modo de teste)",
    }.get(name, name)


def _tts_label(name: str) -> str:
    return {
        "edge": "Microsoft Edge (edge-tts), vozes de catálogo",
        "mock": "simuladas (modo de teste)",
    }.get(name, name)


app = create_app()
