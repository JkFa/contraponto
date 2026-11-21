"""Verification rules (claims × confronto / internal exam) and verification.md rendering."""

from __future__ import annotations

from app.models import Script

STATUS_LABEL = {
    "apoiada": "Apoiada",
    "contestada": "Contestada",
    "parcial": "Parcial",
    "nao_verificavel": "Não verificável",
}
EVIDENCE_LABEL = {
    "confronto": "material de confronto",
    "primaria": "fonte primária",
    "interna": "exame interno",
}


def validate_verification(script: Script, has_confronto: bool) -> list[str]:
    """Check the verification block against docs/04 §4.1 rule 3 and §3.4."""
    errors: list[str] = []
    items = script.verification
    if not 3 <= len(items) <= 8:
        errors.append(f"'verification' deve ter de 3 a 8 itens (veio com {len(items)}).")
    for i, item in enumerate(items, start=1):
        if not item.note.strip():
            errors.append(f"Item {i} de 'verification' está sem 'note' explicando o status.")
        if not item.claim.strip():
            errors.append(f"Item {i} de 'verification' está sem 'claim'.")
    if not script.verdict.strip():
        errors.append("'verdict' está vazio: feche com um veredito curto e honesto.")

    confronto_turns = [t for t in script.turns if t.kind == "confronto"]
    if has_confronto:
        if items and not any(i.evidence_role == "confronto" for i in items):
            errors.append(
                "Há material de confronto, mas nenhum item de 'verification' usa "
                "evidence_role='confronto'."
            )
        if any(i.evidence_role != "interna" for i in items) and not confronto_turns:
            errors.append(
                "Itens de 'verification' apoiados no confronto exigem ao menos um turno "
                "kind='confronto' no roteiro."
            )
    else:
        bad = [n for n, i in enumerate(items, start=1) if i.evidence_role != "interna"]
        if bad:
            errors.append(
                "Sem material de confronto, todos os itens de 'verification' devem usar "
                f"evidence_role='interna' (itens {', '.join(map(str, bad))})."
            )
        if confronto_turns:
            errors.append("Sem material de confronto, nenhum turno pode usar kind='confronto'.")
    return errors


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_verification_md(script: Script, examined: str, confronted_with: str | None) -> str:
    basis = (
        f'confrontado com "{confronted_with}"'
        if confronted_with
        else "por exame de consistência interna (sem material de confronto)"
    )
    lines = [
        "# Verificação",
        "",
        f'Exame de "{_cell(examined)}", {basis}.',
        "",
        "| Afirmação | Status | Nota |",
        "|---|---|---|",
    ]
    for item in script.verification:
        claim = _cell(item.claim) + (f" ({item.claim_ts})" if item.claim_ts else "")
        status = f"{STATUS_LABEL[item.status]} · {EVIDENCE_LABEL[item.evidence_role]}"
        lines.append(f"| {claim} | {status} | {_cell(item.note)} |")
    lines += [
        "",
        f"**Veredito:** {script.verdict.strip()}",
        "",
        "> Episódio gerado com IA. As vozes são sintéticas. O veredito é a conclusão deste "
        "episódio, com base no material apresentado, e pode divergir das fontes originais.",
        "",
    ]
    return "\n".join(lines)
