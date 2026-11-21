from __future__ import annotations

import asyncio
import copy
import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.llm import prompts
from app.llm.base import GenerationContext, LLMError
from app.llm.mock import MockProvider, build_mock_script
from app.models import Script
from app.script_service import (
    ScriptError,
    check_rules,
    condense,
    generate_script,
    validate_user_script,
    verify_citations,
)
from tests.conftest import CONFRONTO_TEXT, PRIMARY_TEXT, material


class Scripted:
    """Fake provider returning queued responses and recording prompts."""

    name = "gemini"

    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    async def generate(self, system: str, user: str, ctx: GenerationContext) -> str:
        self.calls.append((system, user))
        item = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)


def ctx(confronto: bool, mode: str = "react", ts: bool = False, **kw: Any) -> GenerationContext:
    return GenerationContext(
        task="script",
        mode=mode,  # type: ignore[arg-type]
        duration_min=kw.pop("duration_min", 3),
        thesis=kw.pop("thesis", "O texto exagera." if mode == "critica" else None),
        primary=material("primaria", PRIMARY_TEXT, ts=ts),
        confronto=material("confronto", CONFRONTO_TEXT) if confronto else None,
        **kw,
    )


def good(c: GenerationContext) -> dict[str, Any]:
    return build_mock_script(c)


def run(coro):
    return asyncio.run(coro)


# ---------- happy paths ----------


def test_with_confronto_produces_confronto_verification() -> None:
    c = ctx(True)
    script, provider = run(generate_script([MockProvider()], c))
    assert provider == "mock"
    assert 3 <= len(script.verification) <= 8
    assert any(v.evidence_role == "confronto" for v in script.verification)
    assert any(t.kind == "confronto" for t in script.turns)
    assert {v.status for v in script.verification} >= {"apoiada", "contestada", "parcial"}
    assert script.verdict
    assert script.fidelity_notes == []


def test_without_confronto_uses_internal_exam() -> None:
    script, _ = run(generate_script([MockProvider()], ctx(False)))
    assert all(v.evidence_role == "interna" for v in script.verification)
    assert not any(t.kind == "confronto" for t in script.turns)


def test_timestamps_required_and_present() -> None:
    script, _ = run(generate_script([MockProvider()], ctx(False, ts=True)))
    quotes = [t for t in script.turns if t.kind == "citacao"]
    assert quotes and all(t.source_ts for t in quotes)


def test_master_prompt_always_sent_and_mode_prompts() -> None:
    for mode in ("critica", "react"):
        c = ctx(False, mode=mode)
        fake = Scripted(good(c))
        run(generate_script([fake], c, instructions="mais curto"))
        system, user = fake.calls[0]
        assert prompts.MASTER_PROMPT in system
        assert "EXAME INTERNO" in system
        assert ("MODO: CRÍTICA" in user) == (mode == "critica")
        assert ("MODO: REACT" in user) == (mode == "react")
        assert user.rstrip().endswith('"""mais curto"""')
        assert "AJUSTES PEDIDOS PELO USUÁRIO" in user


def test_critica_includes_thesis_and_confronto_material() -> None:
    c = ctx(True, mode="critica", thesis="Minha tese: correlação não é causa.")
    fake = Scripted(good(c))
    run(generate_script([fake], c))
    _, user = fake.calls[0]
    assert "Minha tese: correlação não é causa." in user
    assert "Dados oficiais mostram" in user


# ---------- validation & repair ----------


def _bad(c: GenerationContext, mutate) -> dict[str, Any]:
    data = copy.deepcopy(good(c))
    mutate(data)
    return data


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(verification=d["verification"][:2]),
        lambda d: d.update(verification=d["verification"] * 3),
        lambda d: d["verification"][0].update(note="  "),
        lambda d: d.update(verdict=""),
        lambda d: d.pop("verdict"),
        lambda d: d.pop("verification"),
    ],
    ids=["<3 items", ">8 items", "empty note", "empty verdict", "no verdict", "no verification"],
)
def test_invalid_verification_is_repaired(mutate) -> None:
    c = ctx(True)
    fake = Scripted(_bad(c, mutate), good(c))
    script, _ = run(generate_script([fake], c))
    assert len(fake.calls) == 2
    assert "REJEITADA" in fake.calls[1][1]
    assert prompts.MASTER_PROMPT in fake.calls[1][0]  # master prompt intact on repair
    assert 3 <= len(script.verification) <= 8


def test_invalid_three_times_fails() -> None:
    c = ctx(True)
    bad = _bad(c, lambda d: d.update(verdict=""))
    fake = Scripted(bad)
    with pytest.raises(ScriptError) as exc:
        run(generate_script([fake], c))
    assert exc.value.code == "SCRIPT_INVALID"
    assert len(fake.calls) == 3


def test_non_json_is_repaired() -> None:
    c = ctx(False)
    fake = Scripted("desculpe, não sei", "```json\n" + json.dumps(good(c)) + "\n```")
    script, _ = run(generate_script([fake], c))
    assert script.title


def _citation(text: str, role: str, ts: str | None = None) -> dict[str, Any]:
    t = {"speaker": "HOST_1", "kind": "citacao", "text": text, "role": role}
    if ts:
        t["source_ts"] = ts
    return t


def _script(c: GenerationContext, **changes: Any) -> Script:
    data = good(c)
    data.update(changes)
    return Script.model_validate(data)


def test_four_quotes_same_source_rejected() -> None:
    c = ctx(True)
    data = good(c)
    data["turns"] += [_citation("O consumo de café cresceu", "primaria") for _ in range(3)]
    report = check_rules(Script.model_validate(data), c.primary, c.confronto, None)
    assert any("máximo é 3" in e for e in report.hard)


def test_three_quotes_per_source_allowed_separately() -> None:
    c = ctx(True)
    data = good(c)
    data["turns"] = [t for t in data["turns"] if t["kind"] != "citacao"]
    data["turns"] += [_citation("O consumo de café cresceu", "primaria") for _ in range(3)]
    data["turns"] += [_citation("Pediatras não recomendam cafeína", "confronto") for _ in range(3)]
    report = check_rules(Script.model_validate(data), c.primary, c.confronto, None)
    assert report.hard == []


def test_long_quote_rejected() -> None:
    c = ctx(False)
    data = good(c)
    data["turns"].append(_citation(" ".join(["palavra"] * 16), "primaria"))
    report = check_rules(Script.model_validate(data), c.primary, None, None)
    assert any("15 palavras" in e for e in report.hard)


def test_wrong_role_quote_rejected() -> None:
    c = ctx(True)
    data = good(c)
    data["turns"].append(_citation("Pediatras não recomendam cafeína para crianças", "primaria"))
    report = check_rules(Script.model_validate(data), c.primary, c.confronto, None)
    assert any("vem da fonte 'confronto'" in e for e in report.hard)

    data = good(c)
    data["turns"].append(_citation("todo mundo que toma café vive mais", "confronto"))
    report = check_rules(Script.model_validate(data), c.primary, c.confronto, None)
    assert any("vem da fonte 'primaria'" in e for e in report.hard)


def test_quote_needs_ts_when_source_has_timestamps() -> None:
    c = ctx(False, ts=True)
    data = good(c)
    data["turns"].append(_citation("O consumo de café cresceu", "primaria"))
    report = check_rules(Script.model_validate(data), c.primary, None, None)
    assert any("source_ts" in e for e in report.hard)


def test_citacao_without_role_rejected() -> None:
    c = ctx(False)
    data = good(c)
    data["turns"].append({"speaker": "HOST_1", "kind": "citacao", "text": "café"})
    report = check_rules(Script.model_validate(data), c.primary, None, None)
    assert any("precisa de 'role'" in e for e in report.hard)


def test_missing_quote_becomes_fidelity_note() -> None:
    c = ctx(True)
    data = good(c)
    data["turns"].append(_citation("frase que ninguém disse jamais aqui", "primaria"))
    notes = verify_citations(Script.model_validate(data), c.primary, c.confronto)
    assert notes == [
        f"Citação do turno {len(data['turns'])} (fonte primaria) não encontrada — confira."
    ]


def test_no_confronto_rejects_confronto_turns_and_roles() -> None:
    c = ctx(False)
    data = good(c)
    data["turns"].append(
        {"speaker": "HOST_2", "kind": "confronto", "text": "O outro texto diz", "role": "confronto"}
    )
    data["verification"][0]["evidence_role"] = "confronto"
    report = check_rules(Script.model_validate(data), c.primary, None, None)
    joined = " ".join(report.hard)
    assert "evidence_role='interna'" in joined
    assert "role='confronto'" in joined


def test_confronto_requires_confronto_item_and_turn() -> None:
    c = ctx(True)
    data = good(c)
    for v in data["verification"]:
        v["evidence_role"] = "interna"
    report = check_rules(Script.model_validate(data), c.primary, c.confronto, None)
    assert any("nenhum item" in e for e in report.hard)

    data = good(c)
    data["turns"] = [t for t in data["turns"] if t["kind"] != "confronto"]
    report = check_rules(Script.model_validate(data), c.primary, c.confronto, None)
    assert any("kind='confronto'" in e for e in report.hard)


def test_turn_over_600_chars_rejected_by_schema() -> None:
    c = ctx(False)
    data = good(c)
    data["turns"][0]["text"] = "a" * 601
    with pytest.raises(ValidationError):
        Script.model_validate(data)


def test_alternation_and_length_are_soft_and_reported() -> None:
    c = ctx(False, duration_min=12)
    data = good(ctx(False, duration_min=3))
    for t in data["turns"][:3]:
        t["speaker"] = "HOST_1"
    fake = Scripted(data)
    script, _ = run(generate_script([fake], c))
    assert len(fake.calls) == 3  # tried to repair
    assert any("alternar" in n for n in script.fidelity_notes)
    assert any("palavras" in n for n in script.fidelity_notes)


def test_refusal() -> None:
    fake = Scripted({"refused": True})
    with pytest.raises(ScriptError) as exc:
        run(generate_script([fake], ctx(False)))
    assert exc.value.code == "CONTENT_REFUSED"


def test_provider_fallback_and_errors() -> None:
    c = ctx(False)
    failing = Scripted(LLMError("LLM_QUOTA"))
    ok = Scripted(good(c))
    ok.name = "groq"
    _, provider = run(generate_script([failing, ok], c))
    assert provider == "groq"
    with pytest.raises(LLMError) as exc:
        run(generate_script([Scripted(LLMError("LLM_QUOTA"))], c))
    assert exc.value.code == "LLM_QUOTA"


def test_user_edit_validation() -> None:
    c = ctx(True)
    script = _script(c)
    validate_user_script(script, c.primary, c.confronto)
    script.verification[0].note = ""
    with pytest.raises(ScriptError):
        validate_user_script(script, c.primary, c.confronto)


def test_map_reduce_when_over_limit(monkeypatch) -> None:
    import app.script_service as svc

    monkeypatch.setitem(svc.TOKEN_LIMITS, "mock", 10)
    c = ctx(True)
    prim, conf = run(condense([MockProvider()], c.primary, c.confronto, c))
    assert prim and conf
    assert len(prim) < len(c.primary.formatted())
    assert len(conf) < len(c.confronto.formatted())
