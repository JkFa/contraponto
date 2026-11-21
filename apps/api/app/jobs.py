"""In-memory episode registry: state machine, SSE pub/sub, render queue and TTL cleanup."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import secrets
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import Settings
from app.errors import MESSAGES, ApiError
from app.ingest.material import Material
from app.ingest.normalize import normalize
from app.ingest.youtube import canonical_url, ingest_youtube
from app.llm.base import GenerationContext, LLMError, LLMProvider
from app.mix import MixError, mix_episode
from app.models import AudioInfo, Episode, ErrorInfo, Mode, Script, Source, Status, Tone
from app.script_service import ScriptError, generate_script
from app.storage import Storage
from app.tts.base import TTSError, TTSProvider, Voice
from app.tts.prepare import tts_prepare

log = logging.getLogger("contraponto.jobs")

TERMINAL_EVENTS = {"done", "error"}


@dataclass
class PendingInput:
    """A source as received: either already parsed (text/file) or a YouTube id to fetch."""

    role: str
    material: Material | None = None
    video_id: str | None = None

    def placeholder(self) -> Source:
        if self.material is not None:
            return self.material.to_source()
        return Source(
            role=self.role,  # type: ignore[arg-type]
            kind="youtube",
            url=canonical_url(self.video_id or ""),
            has_timestamps=True,
        )


@dataclass
class EpisodeRecord:
    id: str
    mode: Mode
    tone: Tone
    duration_min: int
    hosts: tuple[str, str]
    thesis: str | None
    focus_points: str | None
    primary_input: PendingInput
    confronto_input: PendingInput | None
    created_at: datetime
    expires_at: datetime
    status: Status = "created"
    primary: Material | None = None
    confronto: Material | None = None
    script: Script | None = None
    audio: AudioInfo | None = None
    error: ErrorInfo | None = None
    llm_used: str = ""
    tts_used: str = ""
    gemini_key: str | None = field(default=None, repr=False)  # BYOK: memory only, never logged
    last_event: tuple[str, dict[str, Any]] | None = None
    subscribers: list[asyncio.Queue[tuple[str, dict[str, Any]]]] = field(default_factory=list)
    task: asyncio.Task[None] | None = field(default=None, repr=False)

    @property
    def sources(self) -> list[Source]:
        out = [self.primary.to_source() if self.primary else self.primary_input.placeholder()]
        if self.confronto:
            out.append(self.confronto.to_source())
        elif self.confronto_input:
            out.append(self.confronto_input.placeholder())
        return out

    def expired(self, now: datetime | None = None) -> bool:
        return (now or datetime.now(UTC)) >= self.expires_at


LLMFactory = Callable[[Settings, str | None], Sequence[LLMProvider]]
TTSFactory = Callable[[Settings], TTSProvider]


def default_llm_factory(settings: Settings, byok: str | None) -> list[LLMProvider]:
    from app.llm.gemini import GeminiProvider
    from app.llm.groq import GroqProvider
    from app.llm.mock import MockProvider

    if settings.llm_name == "mock":
        return [MockProvider()]
    timeout, delays = settings.llm_timeout_s, settings.llm_retry_delays
    gemini_key = byok or settings.gemini_api_key
    gemini = (
        [GeminiProvider(gemini_key, settings.gemini_model, timeout, delays)] if gemini_key else []
    )
    groq = (
        [GroqProvider(settings.groq_api_key, settings.groq_model, timeout, delays)]
        if settings.groq_api_key
        else []
    )
    chain: list[LLMProvider] = (
        [*groq, *gemini]
        if settings.llm_provider == "groq"
        else [
            *gemini,
            *groq,
        ]
    )
    return chain


def default_tts_factory(settings: Settings) -> TTSProvider:
    from app.tts.edge import EdgeTTS
    from app.tts.mock import MockTTS

    return MockTTS() if settings.tts_name == "mock" else EdgeTTS()


def new_id() -> str:
    return secrets.token_urlsafe(9)


class JobManager:
    def __init__(
        self,
        settings: Settings,
        storage: Storage,
        llm_factory: LLMFactory = default_llm_factory,
        tts_factory: TTSFactory = default_tts_factory,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.llm_factory = llm_factory
        self.tts_factory = tts_factory
        self.episodes: dict[str, EpisodeRecord] = {}
        self._render_sem: asyncio.Semaphore | None = None
        self._tasks: set[asyncio.Task[Any]] = set()
        self.active_renders = 0
        self.peak_renders = 0

    # ---------- registry ----------
    @property
    def render_sem(self) -> asyncio.Semaphore:
        if self._render_sem is None:
            self._render_sem = asyncio.Semaphore(max(1, self.settings.max_concurrent_renders))
        return self._render_sem

    def create(self, **kwargs: Any) -> EpisodeRecord:
        now = datetime.now(UTC)
        rec = EpisodeRecord(
            id=new_id(),
            created_at=now,
            expires_at=now + timedelta(hours=self.settings.episode_ttl_hours),
            **kwargs,
        )
        self.episodes[rec.id] = rec
        log.info(
            "episode created id=%s mode=%s confronto=%s",
            rec.id,
            rec.mode,
            rec.confronto_input is not None,
        )
        return rec

    def get(self, episode_id: str) -> EpisodeRecord:
        rec = self.episodes.get(episode_id)
        if rec is None or rec.expired():
            if rec is not None:
                self.delete(episode_id)
            raise ApiError("EXPIRED", 404)
        return rec

    def delete(self, episode_id: str) -> None:
        rec = self.episodes.pop(episode_id, None)
        if rec and rec.task and not rec.task.done():
            rec.task.cancel()
        self.storage.delete(episode_id)

    def cleanup(self) -> int:
        now = datetime.now(UTC)
        expired = [eid for eid, rec in self.episodes.items() if rec.expired(now)]
        for eid in expired:
            self.delete(eid)
        self.storage.purge_orphans(set(self.episodes))
        self.storage.purge_cache(self.settings.episode_ttl_hours * 3600)
        if expired:
            log.info("cleanup removed=%d", len(expired))
        return len(expired)

    async def cleanup_loop(self, interval_s: float = 600) -> None:
        while True:
            await asyncio.sleep(interval_s)
            with contextlib.suppress(Exception):
                self.cleanup()

    def to_episode(self, rec: EpisodeRecord) -> Episode:
        base = self.settings.public_base_url.rstrip("/")
        return Episode(
            id=rec.id,
            status=rec.status,
            mode=rec.mode,
            created_at=rec.created_at.isoformat(),
            expires_at=rec.expires_at.isoformat(),
            sources=rec.sources,
            script=rec.script,
            audio=rec.audio,
            share_url=f"{base}/s/{rec.id}",
            error=rec.error,
        )

    # ---------- events ----------
    def subscribe(self, rec: EpisodeRecord) -> asyncio.Queue[tuple[str, dict[str, Any]]]:
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        rec.subscribers.append(queue)
        return queue

    def unsubscribe(self, rec: EpisodeRecord, queue: asyncio.Queue[Any]) -> None:
        with contextlib.suppress(ValueError):
            rec.subscribers.remove(queue)

    def current_event(self, rec: EpisodeRecord) -> tuple[str, dict[str, Any]]:
        if rec.status == "failed" and rec.error:
            return "error", {"code": rec.error.code, "message": rec.error.message}
        if rec.status in ("script_ready", "ready"):
            return "done", {"status": rec.status}
        if rec.last_event:
            return rec.last_event
        return "progress", {"status": rec.status, "step": "Na fila", "pct": 0}

    async def publish(self, rec: EpisodeRecord, event: str, data: dict[str, Any]) -> None:
        if event == "progress":
            rec.last_event = (event, data)
        for queue in list(rec.subscribers):
            queue.put_nowait((event, data))
        await asyncio.sleep(0)

    async def progress(self, rec: EpisodeRecord, status: Status, step: str, pct: int) -> None:
        rec.status = status
        await self.publish(rec, "progress", {"status": status, "step": step, "pct": pct})

    async def fail(self, rec: EpisodeRecord, code: str, message: str | None = None) -> None:
        rec.status = "failed"
        rec.error = ErrorInfo(
            code=code, message=message or MESSAGES.get(code, MESSAGES["INTERNAL"])
        )
        log.info("episode failed id=%s code=%s", rec.id, code)
        await self.publish(rec, "error", {"code": rec.error.code, "message": rec.error.message})

    def _spawn(self, rec: EpisodeRecord, coro: Any) -> None:
        task = asyncio.create_task(coro)
        rec.task = task
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    # ---------- scripting ----------
    def start_scripting(self, rec: EpisodeRecord) -> None:
        self._spawn(rec, self._ingest_and_script(rec))

    def start_regenerate(self, rec: EpisodeRecord, instructions: str | None) -> None:
        if rec.status not in ("script_ready", "failed") or (
            rec.status == "failed" and (rec.script is None or rec.primary is None)
        ):
            raise ApiError("INVALID_STATE", 409)
        rec.error = None
        rec.audio = None
        rec.status = "scripting"
        rec.last_event = None
        self._spawn(rec, self._script_stage(rec, instructions))

    async def _materialize(self, pending: PendingInput) -> Material:
        if pending.material is not None:
            return pending.material
        assert pending.video_id is not None
        return await asyncio.to_thread(
            ingest_youtube,
            pending.video_id,
            pending.role,
            self.storage.cache,  # type: ignore[arg-type]
        )

    async def _ingest_and_script(self, rec: EpisodeRecord) -> None:
        started = time.monotonic()
        try:
            await self.progress(rec, "ingesting", "Lendo a fonte primária", 10)
            primary = await self._materialize(rec.primary_input)
            confronto = None
            if rec.confronto_input:
                await self.progress(rec, "ingesting", "Lendo o material de confronto", 20)
                confronto = await self._materialize(rec.confronto_input)
            await self.progress(rec, "ingesting", "Organizando o conteúdo", 25)
            rec.primary = normalize(primary)
            rec.confronto = normalize(confronto) if confronto else None
            if not rec.primary.segments:
                raise ApiError("FILE_UNSUPPORTED", 422)
        except ApiError as exc:
            await self.fail(rec, exc.code, exc.message)
            return
        except Exception:  # noqa: BLE001
            log.exception("ingest crashed id=%s", rec.id)
            await self.fail(rec, "INTERNAL")
            return
        log.info("ingest done id=%s ms=%d", rec.id, (time.monotonic() - started) * 1000)
        await self._script_stage(rec, None)

    async def _script_stage(self, rec: EpisodeRecord, instructions: str | None) -> None:
        started = time.monotonic()
        rec.status = "scripting"
        providers = self.llm_factory(self.settings, rec.gemini_key)
        if not providers:
            await self.fail(rec, "LLM_NOT_CONFIGURED")
            return
        ctx = GenerationContext(
            task="script",
            mode=rec.mode,
            tone=rec.tone,
            duration_min=rec.duration_min,
            hosts=rec.hosts,
            thesis=rec.thesis,
            focus_points=rec.focus_points,
            primary=rec.primary,
            confronto=rec.confronto,
        )

        async def on_step(step: str, pct: int) -> None:
            await self.progress(rec, "scripting", step, pct)

        try:
            script, provider = await generate_script(providers, ctx, instructions, on_step)
        except (LLMError, ScriptError) as exc:
            await self.fail(rec, exc.code)
            return
        except Exception:  # noqa: BLE001
            log.exception("scripting crashed id=%s", rec.id)
            await self.fail(rec, "LLM_FAILED")
            return
        rec.script = script
        rec.llm_used = provider
        rec.error = None
        log.info(
            "script ready id=%s llm=%s ms=%d", rec.id, provider, (time.monotonic() - started) * 1000
        )
        await self.progress(rec, "script_ready", "Roteiro pronto para revisão", 100)
        await self.publish(rec, "done", {"status": "script_ready"})

    # ---------- render ----------
    def start_render(self, rec: EpisodeRecord) -> None:
        if rec.status != "script_ready" or rec.script is None:
            raise ApiError("INVALID_STATE", 409)
        rec.status = "rendering"
        rec.last_event = (
            "progress",
            {"status": "rendering", "step": "Na fila do estúdio", "pct": 5},
        )
        self._spawn(rec, self._render(rec))

    def _voices(self) -> dict[str, Voice]:
        s = self.settings
        return {
            "HOST_1": Voice(s.voice_host_1, "+0%", "+0Hz", tone_hz=220),
            "HOST_2": Voice(s.voice_host_2, "+3%", "+2Hz", tone_hz=330),
        }

    async def _render(self, rec: EpisodeRecord) -> None:
        assert rec.script is not None
        await self.publish(rec, "progress", rec.last_event[1] if rec.last_event else {})
        async with self.render_sem:
            self.active_renders += 1
            self.peak_renders = max(self.peak_renders, self.active_renders)
            try:
                await self._render_inner(rec)
            finally:
                self.active_renders -= 1

    async def _render_inner(self, rec: EpisodeRecord) -> None:
        assert rec.script is not None
        started = time.monotonic()
        script = rec.script
        tts = self.tts_factory(self.settings)
        voices = self._voices()
        work = self.storage.episode_dir(rec.id) / "turns"
        work.mkdir(parents=True, exist_ok=True)
        total = len(script.turns)
        done = 0
        sem = asyncio.Semaphore(3)
        lock = asyncio.Lock()

        async def synth(i: int) -> Any:
            nonlocal done
            turn = script.turns[i]
            async with sem:
                path = await tts.synthesize(
                    tts_prepare(turn.text), voices[turn.speaker], work / f"t{i:03d}"
                )
            async with lock:
                done += 1
                pct = 10 + int(75 * done / total)
                await self.progress(rec, "rendering", f"Gravando as vozes ({done}/{total})", pct)
            return path

        try:
            await self.progress(rec, "rendering", f"Gravando as vozes (0/{total})", 10)
            files = await asyncio.gather(*(synth(i) for i in range(total)))
            await self.progress(rec, "rendering", "Mixando o episódio", 90)
            primary = rec.sources[0]
            result = await mix_episode(
                list(files),
                script.turns,
                work / "mix",
                self.storage.audio_path(rec.id),
                seed=rec.id,
                tags={
                    "title": script.title,
                    "artist": "Contraponto (vozes sintéticas)",
                    "album": "Contraponto · Gerado com IA",
                    "comment": primary.url or "Fonte primária enviada pelo usuário",
                },
            )
        except (TTSError, MixError) as exc:
            log.warning("render failed id=%s err=%s", rec.id, type(exc).__name__)
            await self.fail(rec, "TTS_FAILED")
            return
        except Exception:  # noqa: BLE001
            log.exception("render crashed id=%s", rec.id)
            await self.fail(rec, "TTS_FAILED")
            return
        finally:
            for f in work.glob("t*.*"):
                f.unlink(missing_ok=True)
        base = self.settings.public_base_url.rstrip("/")
        rec.audio = AudioInfo(
            url=f"{base}/api/episodes/{rec.id}/audio.mp3",
            duration_s=result.duration_s,
            bytes=result.bytes,
        )
        rec.tts_used = tts.name
        log.info(
            "render done id=%s tts=%s ms=%d", rec.id, tts.name, (time.monotonic() - started) * 1000
        )
        await self.progress(rec, "ready", "Episódio pronto", 100)
        await self.publish(rec, "done", {"status": "ready"})
