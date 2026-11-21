"""Deterministic mock LLM: builds a valid script from the materials, without network."""

from __future__ import annotations

import json
import re

from app.ingest.material import Material, format_ts
from app.llm.base import GenerationContext

FILLER_OPINIAO = [
    "Na nossa avaliação, o ponto mais forte aqui é quando o argumento vem com um número que dá "
    "para conferir. Onde aparece só a impressão de quem fala, a gente precisa segurar o "
    "entusiasmo e marcar isso como opinião, não como fato estabelecido.",
    "Calma lá, vale separar as coisas. Uma coisa é o que o material afirma, outra é o que dá "
    "para sustentar com o que temos em mãos. A gente está falando da segunda, e com cuidado "
    "para não colocar palavras na boca de ninguém.",
    "Pois é, e repara que isso muda o peso da conclusão. Se a premissa não tem dado, a "
    "conclusão também fica mais frágil, por mais bem contada que seja a história.",
    "Exato. E aqui entra um cuidado com o ouvinte: o que a gente está fazendo é examinar os "
    "argumentos, não julgar as pessoas. Dá para discordar do raciocínio e ainda reconhecer o "
    "que ele tem de bom.",
]
FILLER_PERGUNTA = [
    "Mas deixa eu te perguntar uma coisa: se você tivesse que defender esse ponto diante de "
    "alguém bem cético, qual seria o melhor argumento a favor dele?",
    "E o que ficou de fora? Tem algum contexto que, se aparecesse, mudaria o sentido do que "
    "foi dito?",
    "Então o que o ouvinte deveria conferir por conta própria depois de ouvir a gente?",
]


def _sentences(material: Material | None, limit: int = 6) -> list[tuple[int | None, str]]:
    if material is None:
        return []
    out: list[tuple[int | None, str]] = []
    for ts, text in material.segments:
        for sent in re.split(r"(?<=[.!?])\s+", text):
            sent = sent.strip()
            if len(sent.split()) >= 4:
                out.append((ts, sent))
            if len(out) >= limit:
                return out
    if not out:
        out = [(ts, text) for ts, text in material.segments[:limit] if text.strip()]
    return out


def _quote(ts: int | None, text: str, max_words: int = 12) -> tuple[str, str | None]:
    words = text.split()[:max_words]
    return " ".join(words), (format_ts(ts) if ts is not None else None)


def _clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def build_mock_script(ctx: GenerationContext) -> dict[str, object]:
    h1, h2 = ctx.hosts
    primary = ctx.primary
    conf = ctx.confronto
    p_name = (primary.title if primary and primary.title else "o material enviado") or ""
    p_author = f", de {primary.author}" if primary and primary.author else ""
    p_sents = _sentences(primary, 6) or [(None, "O material apresenta uma ideia central.")]
    c_sents = _sentences(conf, 4)

    turns: list[dict[str, object]] = []

    def add(kind: str, text: str, role: str | None = None, ts: str | None = None) -> None:
        turn: dict[str, object] = {"kind": kind, "text": _clip(text, 600)}
        if role:
            turn["role"] = role
        if ts:
            turn["source_ts"] = ts
        turns.append(turn)

    intro = f"Olá, eu sou {h1} e hoje a gente examina {p_name}{p_author}. " + (
        "E trouxemos um material de confronto para checar o que ele afirma."
        if conf
        else "Sem um segundo material, vamos examinar a consistência interna da fonte."
    )
    add("contexto", intro)
    add("pergunta", f"E eu sou {h2}. Então vamos direto ao ponto: o que a fonte afirma, afinal?")
    q_text, q_ts = _quote(*p_sents[0])
    add("contexto", f"O ponto de partida é este: {_clip(p_sents[0][1], 200)}")
    add("citacao", q_text, "primaria", q_ts if primary and primary.has_timestamps else None)
    if ctx.mode == "critica" and ctx.thesis:
        add("opiniao", f"Na nossa avaliação, a crítica aqui é esta: {_clip(ctx.thesis, 300)}")
    else:
        add("opiniao", "Na nossa avaliação, vale olhar com calma antes de comprar a ideia.")
    if conf and c_sents:
        c_text, c_ts = _quote(*c_sents[0])
        add(
            "confronto",
            f"Só que o material de confronto diz outra coisa: {_clip(c_sents[0][1], 220)}",
            "confronto",
        )
        add("citacao", c_text, "confronto", c_ts if conf.has_timestamps else None)
    else:
        add("transicao", "Sem confronto externo, a régua é a coerência do próprio material.")

    # verification
    statuses_conf = ["apoiada", "contestada", "parcial", "nao_verificavel"]
    statuses_int = ["parcial", "nao_verificavel", "apoiada", "contestada"]
    notes_conf = {
        "apoiada": "O material de confronto traz dado que vai na mesma direção.",
        "contestada": "O material de confronto apresenta informação que contradiz este ponto.",
        "parcial": "O confronto confirma parte da afirmação, mas não o alcance dado a ela.",
        "nao_verificavel": "O material de confronto não trata deste ponto.",
    }
    notes_int = {
        "apoiada": "A conclusão segue das premissas apresentadas no próprio material.",
        "contestada": "Há contradição com outro trecho do próprio material.",
        "parcial": "A afirmação tem base, mas generaliza além do que os dados mostram.",
        "nao_verificavel": "Afirmação solta, sem dado ou fonte citada que a sustente.",
    }
    verification: list[dict[str, object]] = []
    for i, (ts, sent) in enumerate(p_sents[:4]):
        status = (statuses_conf if conf else statuses_int)[i % 4]
        item: dict[str, object] = {
            "claim": _clip(sent, 220),
            "status": status,
            "note": (notes_conf if conf else notes_int)[status],
            "evidence_role": "confronto" if conf else "interna",
        }
        if ts is not None and primary and primary.has_timestamps:
            item["claim_ts"] = format_ts(ts)
        verification.append(item)
    while len(verification) < 3:
        verification.append(
            {
                "claim": "O material sugere uma conclusão geral a partir de poucos exemplos.",
                "status": "nao_verificavel",
                "note": "Generalização sem dado que a sustente.",
                "evidence_role": "confronto" if conf else "interna",
            }
        )

    for i, item in enumerate(verification[1:], start=1):
        add("contexto", f"Outro ponto da fonte: {item['claim']}")
        add("opiniao", f"E aqui o exame diz: {item['note']}")
        if i % 2 == 0:
            add("pergunta", FILLER_PERGUNTA[i % len(FILLER_PERGUNTA)])

    target = ctx.duration_min * 150
    verdict = (
        "Com base no que temos aqui: parte do argumento se sustenta, parte é contestada e "
        "alguns pontos ficam em aberto. Vale conferir as fontes antes de concluir."
    )
    closing = f"Fechando, {verdict.lower()} Obrigado por ouvir."

    def words() -> int:
        return sum(len(str(t["text"]).split()) for t in turns) + len(closing.split())

    i = 0
    while words() < target * 0.9:
        if i % 3 == 2:
            add("pergunta", FILLER_PERGUNTA[i % len(FILLER_PERGUNTA)])
        else:
            add("opiniao", FILLER_OPINIAO[i % len(FILLER_OPINIAO)])
        i += 1
    add("opiniao", closing)

    for idx, turn in enumerate(turns):
        turn["speaker"] = "HOST_1" if idx % 2 == 0 else "HOST_2"

    title = _clip(f"Examinando {p_name}", 90)
    return {
        "title": title,
        "summary": _clip(
            "Um exame em duas vozes: o que a fonte afirma, o que se sustenta e o que fica em "
            "aberto" + (", com material de confronto." if conf else ", por consistência interna."),
            280,
        ),
        "hosts": {"HOST_1": h1, "HOST_2": h2},
        "turns": turns,
        "verification": verification,
        "verdict": verdict,
        "fidelity_notes": [],
    }


class MockProvider:
    name = "mock"

    async def generate(self, system: str, user: str, ctx: GenerationContext) -> str:
        if ctx.task == "summarize":
            words = ctx.chunk_text.split()
            return " ".join(words[: max(20, len(words) // 4)])
        return json.dumps(build_mock_script(ctx), ensure_ascii=False)
