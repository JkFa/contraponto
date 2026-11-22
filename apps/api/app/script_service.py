"""Script generation: master prompt + mode prompt → validate → repair → verify citations."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from pydantic import ValidationError
from rapidfuzz import fuzz

from app.ingest.material import Material
from app.ingest.normalize import chunk_segments, estimate_tokens
from app.llm import prompts
from app.llm.base import GenerationContext, LLMError, LLMProvider
from app.models import Script
from app.verification import validate_verification

log = logging.getLogger("contraponto.script")

WORDS_PER_MIN = 150
MAX_QUOTES_PER_SOURCE = 3
MAX_QUOTE_WORDS = 15
SIMILARITY = 85
MAX_REPAIRS = 2
TOKEN_LIMITS = {"gemini": 900_000, "groq": 90_000, "mock": 900_000}

Progress = Callable[[str, int], Awaitable[None]]


class ScriptError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(code)


@dataclass
class Report:
    hard: list[str]
    soft: list[str]


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def found_in(quote: str, source_norm: str) -> bool:
    q = norm(quote)
    if not q or not source_norm:
        return False
    if q in source_norm:
        return True
    return fuzz.partial_ratio(q, source_norm, score_cutoff=SIMILARITY) >= SIMILARITY


def word_count(script: Script) -> int:
    return sum(len(t.text.split()) for t in script.turns)


def parse_llm_json(raw: str) -> dict[str, object]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Resposta não contém um objeto JSON.")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("A raiz do JSON deve ser um objeto.")
    return data


def check_rules(
    script: Script,
    primary: Material,
    confronto: Material | None,
    duration_min: int | None,
) -> Report:
    """Validate docs/04 §4.1. `duration_min=None` skips the length check (user edits)."""
    hard: list[str] = []
    soft: list[str] = []
    has_ts = {
        "primaria": primary.has_timestamps,
        "confronto": bool(confronto and confronto.has_timestamps),
    }
    norms = {
        "primaria": norm(primary.plain()),
        "confronto": norm(confronto.plain()) if confronto else "",
    }
    counts = {"primaria": 0, "confronto": 0}

    for n, turn in enumerate(script.turns, start=1):
        if turn.kind in ("citacao", "confronto") and turn.role is None:
            hard.append(f"Turno {n} (kind='{turn.kind}') precisa de 'role' indicando a fonte.")
            continue
        if turn.role == "confronto" and confronto is None:
            hard.append(f"Turno {n} usa role='confronto', mas não há material de confronto.")
            continue
        if turn.kind != "citacao" or turn.role is None:
            continue
        counts[turn.role] += 1
        if len(turn.text.split()) > MAX_QUOTE_WORDS:
            hard.append(f"Citação do turno {n} passa de {MAX_QUOTE_WORDS} palavras.")
        if has_ts[turn.role] and not turn.source_ts:
            hard.append(f"Citação do turno {n} precisa de 'source_ts' (a fonte tem timestamps).")
        other = "confronto" if turn.role == "primaria" else "primaria"
        if (
            norms[other]
            and not found_in(turn.text, norms[turn.role])
            and found_in(turn.text, norms[other])
        ):
            hard.append(
                f"Citação do turno {n} está marcada como role='{turn.role}', "
                f"mas o trecho vem da fonte '{other}'."
            )
    for role, count in counts.items():
        if count > MAX_QUOTES_PER_SOURCE:
            hard.append(
                f"Há {count} citações literais da fonte '{role}'; o máximo é "
                f"{MAX_QUOTES_PER_SOURCE} por fonte."
            )

    hard.extend(validate_verification(script, confronto is not None))

    run = 1
    for prev, cur in zip(script.turns, script.turns[1:], strict=False):
        run = run + 1 if cur.speaker == prev.speaker else 1
        if run > 2:
            soft.append("Os falantes precisam alternar: nunca mais de 2 turnos seguidos do mesmo.")
            break
    if duration_min:
        target = duration_min * WORDS_PER_MIN
        words = word_count(script)
        if not target * 0.8 <= words <= target * 1.2:
            soft.append(
                f"O roteiro tem {words} palavras; o alvo é {target} (±20%, "
                f"entre {int(target * 0.8)} e {int(target * 1.2)})."
            )
    return Report(hard, soft)


def verify_citations(script: Script, primary: Material, confronto: Material | None) -> list[str]:
    """§4.2: look for each quote in the source named by `role` (never the other)."""
    notes: list[str] = []
    norms = {
        "primaria": norm(primary.plain()),
        "confronto": norm(confronto.plain()) if confronto else "",
    }
    for n, turn in enumerate(script.turns, start=1):
        if turn.kind == "citacao" and turn.role and not found_in(turn.text, norms[turn.role]):
            notes.append(f"Citação do turno {n} (fonte {turn.role}) não encontrada — confira.")
    return notes


def validate_user_script(script: Script, primary: Material, confronto: Material | None) -> Script:
    """Validation for PUT /script: hard rules only; recompute fidelity notes."""
    report = check_rules(script, primary, confronto, duration_min=None)
    if report.hard:
        raise ScriptError("SCRIPT_INVALID", " ".join(report.hard))
    script.fidelity_notes = verify_citations(script, primary, confronto)
    return script


async def _call_chain(
    providers: Sequence[LLMProvider], system: str, user: str, ctx: GenerationContext
) -> tuple[str, str]:
    last = LLMError("LLM_NOT_CONFIGURED")
    for provider in providers:
        try:
            return await provider.generate(system, user, ctx), provider.name
        except LLMError as exc:
            log.warning(
                "llm provider=%s failed code=%s detail=%s", provider.name, exc.code, exc.detail
            )
            if exc.code == "CONTENT_REFUSED":
                raise
            last = exc
    raise last


async def condense(
    providers: Sequence[LLMProvider],
    primary: Material,
    confronto: Material | None,
    ctx: GenerationContext,
) -> tuple[str, str]:
    """Map-reduce when the combined materials exceed the smallest provider's context."""
    prim_text = primary.formatted()
    conf_text = confronto.formatted() if confronto else ""
    limit = min(TOKEN_LIMITS.get(p.name, 90_000) for p in providers) if providers else 90_000
    if estimate_tokens(prim_text + conf_text) <= limit:
        return prim_text, conf_text

    async def reduce(material: Material, label: str) -> str:
        parts: list[str] = []
        for chunk in chunk_segments(material.segments):
            chunk_mat = Material(role=material.role, kind=material.kind, segments=chunk)
            sub = GenerationContext(task="summarize", chunk_text=chunk_mat.formatted())
            text, _ = await _call_chain(
                providers,
                prompts.SUMMARIZE_SYSTEM,
                prompts.build_summarize_user(label, chunk_mat.formatted()),
                sub,
            )
            parts.append(text.strip())
        return "\n".join(parts)

    # Both sources are reduced (proportionally, chunk by chunk); confronto is never cut first.
    prim_text = await reduce(primary, "FONTE PRIMÁRIA")
    if confronto:
        conf_text = await reduce(confronto, "MATERIAL DE CONFRONTO")
    return prim_text, conf_text


async def generate_script(
    providers: Sequence[LLMProvider],
    ctx: GenerationContext,
    instructions: str | None = None,
    progress: Progress | None = None,
) -> tuple[Script, str]:
    """Run the full scripting stage. Returns (script, provider_name)."""
    assert ctx.primary is not None
    primary, confronto = ctx.primary, ctx.confronto

    async def step(label: str, pct: int) -> None:
        if progress:
            await progress(label, pct)

    await step(
        "Cruzando as informações" if confronto else "Examinando a consistência do material", 40
    )
    prim_text, conf_text = await condense(providers, primary, confronto, ctx)

    words = ctx.duration_min * WORDS_PER_MIN
    system = prompts.build_system(ctx.hosts, ctx.tone, words)
    base_user = prompts.build_user(
        ctx.mode,
        prim_text,
        conf_text,
        thesis=ctx.thesis,
        focus_points=ctx.focus_points,
        instructions=instructions,
        primary_meta=(primary.title, primary.author, primary.url),
        confronto_meta=(confronto.title, confronto.author, confronto.url)
        if confronto
        else (None, None, None),
    )

    await step("Escrevendo o roteiro", 60)
    user = base_user
    best: tuple[Script, Report] | None = None
    provider_name = ""
    last_errors: list[str] = []
    for attempt in range(MAX_REPAIRS + 1):
        ctx.attempt = attempt
        raw, provider_name = await _call_chain(providers, system, user, ctx)
        errors: list[str]
        try:
            data = parse_llm_json(raw)
            if data.get("refused") is True:
                raise ScriptError("CONTENT_REFUSED")
            data["hosts"] = {"HOST_1": ctx.hosts[0], "HOST_2": ctx.hosts[1]}
            data["fidelity_notes"] = []
            normalize_labels(data, has_confronto=confronto is not None)
            script = Script.model_validate(data)
            report = check_rules(script, primary, confronto, ctx.duration_min)
            if not report.hard:
                best = (script, report)
                if not report.soft:
                    break
            errors = report.hard + report.soft
        except (ValueError, ValidationError) as exc:
            errors = _describe(exc)
        last_errors = errors
        # Validator messages name rules and turn numbers only, never user content.
        log.info("script attempt=%d invalid errors=%s", attempt, " | ".join(errors)[:800])
        if attempt < MAX_REPAIRS:
            user = base_user + prompts.build_repair(raw, errors)

    if best is None:
        raise ScriptError("SCRIPT_INVALID", "; ".join(last_errors)[:500])

    await step("Conferindo as citações e o veredito", 80)
    script, report = best
    # Soft issues that survived the repairs are surfaced to the human reviewer.
    script.fidelity_notes = verify_citations(script, primary, confronto) + [
        f"Aviso do validador: {s}" for s in report.soft
    ]
    return script, provider_name


def normalize_labels(data: dict[str, object], has_confronto: bool) -> None:
    """Fix label-only mistakes in place, without touching what is said.

    Without a confronto source, "confronto" can only be a mislabel: evidence becomes "interna",
    confronto turns become the episode's own analysis ("opiniao"), and quotes can only come from
    the primary source. Missing roles on quotes default to "primaria" when there is one source.
    """
    if has_confronto:
        return
    for item in data.get("verification") or []:
        if isinstance(item, dict) and item.get("evidence_role") != "interna":
            item["evidence_role"] = "interna"
    for turn in data.get("turns") or []:
        if not isinstance(turn, dict):
            continue
        if turn.get("kind") == "confronto":
            turn["kind"] = "opiniao"
            turn.pop("role", None)
        elif turn.get("kind") == "citacao":
            turn["role"] = "primaria"
        elif turn.get("role") == "confronto":
            turn.pop("role", None)


def _describe(exc: Exception) -> list[str]:
    if isinstance(exc, ValidationError):
        out = []
        for err in exc.errors()[:12]:
            loc = ".".join(str(p) for p in err["loc"])
            out.append(f"Campo '{loc}': {err['msg']}")
        return out
    return [f"JSON inválido: {exc}"]
