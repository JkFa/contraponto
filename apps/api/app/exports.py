"""Markdown exports: script.md and sources.md (docs/04 §7-8, docs/08 §9)."""

from __future__ import annotations

from datetime import datetime

from app.ingest.material import Material
from app.models import Script, Source

KIND_LABEL = {
    "contexto": "contexto",
    "citacao": "citação",
    "confronto": "confronto",
    "opiniao": "opinião",
    "pergunta": "pergunta",
    "transicao": "transição",
}
ROLE_LABEL = {"primaria": "fonte primária", "confronto": "material de confronto"}


def source_label(src: Source | Material | None, fallback: str) -> str:
    if src is None:
        return fallback
    return src.title or src.url or fallback


def source_name(src: Source) -> str:
    """Human name for a source: its title/URL, or what kind of upload it was."""
    if src.title or src.url:
        return src.title or src.url or ""
    return "texto colado" if src.kind == "text" else "arquivo enviado"


def legal_text(primary: Source, confronto: Source | None) -> str:
    """docs/08 §9 standard text."""
    title = source_label(primary, "material enviado")
    author = f", de {primary.author}" if primary.author else ""
    url = f" ({primary.url})" if primary.url else ""
    conf = (
        f', confrontado com "{source_label(confronto, "material de confronto")}"'
        if confronto
        else ""
    )
    return (
        f'**Episódio gerado com IA.** As vozes são sintéticas. O conteúdo examina "{title}"'
        f"{author}{url}{conf}. As conclusões são deste episódio e podem divergir das fontes "
        "originais."
    )


def script_md(script: Script, primary: Source, confronto: Source | None) -> str:
    names = {"HOST_1": script.hosts.HOST_1, "HOST_2": script.hosts.HOST_2}
    lines = [f"# {script.title}", "", script.summary, ""]
    lines.append(f"Apresentação: {names['HOST_1']} e {names['HOST_2']} (vozes sintéticas).")
    lines.append("")
    for turn in script.turns:
        name = names[turn.speaker]
        if turn.kind == "citacao":
            where = ROLE_LABEL.get(turn.role or "primaria", "fonte")
            ts = f" [{turn.source_ts}]" if turn.source_ts else ""
            lines.append(f"**{name}** _(citação · {where}{ts})_: “{turn.text}”")
        elif turn.kind == "confronto":
            lines.append(f"**{name}** _(confronto)_: {turn.text}")
        elif turn.kind == "opiniao":
            lines.append(f"**{name}** _(opinião do episódio)_: {turn.text}")
        else:
            lines.append(f"**{name}:** {turn.text}")
        lines.append("")
    lines += ["---", "", f"**Veredito:** {script.verdict}", "", legal_text(primary, confronto), ""]
    return "\n".join(lines)


def _source_line(label: str, src: Source, accessed: datetime) -> str:
    title = src.title or ("texto colado" if src.kind == "text" else "arquivo enviado")
    author = src.author or ("autor não informado")
    url = src.url or "sem URL (conteúdo enviado pelo usuário)"
    return f"- {label}: **{title}** — {author} — {url} (acessado em {accessed:%d/%m/%Y})"


def sources_md(
    script: Script | None,
    primary: Source,
    confronto: Source | None,
    accessed: datetime,
    llm: str,
    tts: str,
    music: str | None = None,
) -> str:
    lines = ["# Fontes e créditos", "", _source_line("Fonte primária", primary, accessed)]
    if confronto:
        lines.append(_source_line("Material de confronto", confronto, accessed))
    lines += [
        "- Este episódio é um exame crítico gerado com apoio de IA, que confronta as fontes",
        "  acima (ou aplica exame de consistência interna, se só houver uma). As vozes são "
        "sintéticas.",
    ]
    quotes = []
    if script:
        for turn in script.turns:
            if turn.kind == "citacao":
                ts = f" [{turn.source_ts}]" if turn.source_ts else ""
                quotes.append(f"  - “{turn.text}” — {ROLE_LABEL.get(turn.role or '', 'fonte')}{ts}")
    lines.append(
        "- Citações literais (máx. 3 por fonte) com timestamp:"
        if quotes
        else "- Citações literais: nenhuma."
    )
    lines += quotes
    lines += [
        f"- Modelo de linguagem: {llm}. Vozes: {tts}.",
        f"- Música: {music or 'sem música'}",
        "",
        "## Descrição sugerida para publicação",
        "",
    ]
    p_title = source_label(primary, "material enviado")
    p_author = primary.author or "autor não informado"
    p_url = primary.url or "conteúdo enviado pelo usuário"
    c_part = (
        f'"{source_label(confronto, "material de confronto")}"'
        if confronto
        else "exame de consistência interna"
    )
    lines += [
        f'> Episódio gerado com IA (vozes sintéticas) examinando "{p_title}" de {p_author} '
        f"({p_url}), confrontado com {c_part}. As conclusões são do episódio e podem divergir "
        "das fontes originais.",
        "",
        legal_text(primary, confronto),
        "",
    ]
    return "\n".join(lines)


def slugify(text: str) -> str:
    import re
    import unicodedata

    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:60] or "episodio"
