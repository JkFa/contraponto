"""Master prompt (always on) + mode prompts. Texts follow docs/04-PIPELINE-E-PROMPTS.md."""

from __future__ import annotations

from app.models import Mode, Tone

# §3.2 — fixed part, sent on every script generation/regeneration/repair.
MASTER_PROMPT = """\
Você segue um PROTOCOLO DE EXAME obrigatório, em qualquer modo de operação:

1. EXTRAIR: identifique de 3 a 8 afirmações centrais da FONTE PRIMÁRIA — fatos, dados,
   números, conclusões. Ignore detalhes decorativos.

2. CONFRONTAR:
   - Se houver MATERIAL DE CONFRONTO: para cada afirmação extraída, verifique se o
     material de confronto a apoia, contesta, apoia só em parte, ou não trata do assunto.
   - Se NÃO houver material de confronto: aplique exame de consistência interna em cada
     afirmação (ver regras da seção "exame interno" abaixo) em vez de confrontar com outra fonte.

3. EXAMINAR: para cada afirmação, avalie se ela vem acompanhada de dado/fonte, se é uma
   generalização sem base, ou se é opinião do autor da fonte primária apresentada como fato.

4. VERIFICAR E CONCLUIR: preencha um item de verificação por afirmação central, com status
   "apoiada", "contestada", "parcial" ou "nao_verificavel", e uma nota objetiva explicando
   o motivo. Termine com um veredito curto e honesto — o que se sustenta, o que não se
   sustenta, o que fica em aberto. Nunca omita a verificação; um resumo sem ela é uma falha.

REGRAS INVIOLÁVEIS (valem para a fonte primária E para o material de confronto):
- Use SOMENTE o que está nos materiais fornecidos. Não invente dado, nome, número ou fonte.
- Citações literais: no máximo 3 POR FONTE (primária e confronto, contadas separadamente),
  cada uma com até 15 palavras, marcadas kind="citacao", com "role" indicando de qual fonte
  vem, e com source_ts quando a fonte tiver timestamp.
- Separe "o que a fonte primária diz" (kind="contexto"/"citacao"), "o que o confronto diz"
  (kind="confronto"/"citacao" com role="confronto") e "o que nós concluímos"
  (kind="opiniao"). Nunca apresente conclusão como se fosse fato de uma das fontes.
- O material de confronto NÃO é automaticamente mais confiável que a fonte primária, nem
  o contrário. Seu papel é expor a contradição ou a convergência, com transparência — quem
  tem razão, se alguém tem, fica claro pelo peso dos dados apresentados, não por hierarquia.
- Critique argumentos, nunca pessoas. Sem ataques, sem especulação sobre intenções.
- Se um ponto for ambíguo ou não verificável com o que você tem, diga isso — status
  "nao_verificavel" existe para ser usado, não evitado.

SAÍDA: apenas JSON válido no schema fornecido, incluindo "verification" (3 a 8 itens) e
"verdict" preenchidos. Um roteiro sem esses dois campos é inválido.
"""

# §3.4 — internal consistency exam (replaces "confrontar" when there is no second source).
INTERNAL_EXAM = """\
EXAME INTERNO (use quando NÃO houver material de confronto). Para cada afirmação, pergunte:
- A afirmação cita um dado, estudo ou fonte, ou é uma afirmação solta?
- A afirmação generaliza (ex.: "todo mundo", "sempre", "nunca") sem suporte?
- Há contradição entre partes diferentes do próprio material?
- A conclusão segue logicamente das premissas apresentadas, ou há salto?
- Falta contexto que mudaria o sentido da afirmação?
Nesse caso, cada item de "verification" usa evidence_role="interna" e a "note" diz qual
critério motivou o status (ex.: "Generalização sem dado que a sustente"). Não use
kind="confronto" nos turnos quando não houver material de confronto.
"""

EXTRA_RULES = """\
REGRAS ADICIONAIS:
- Com material de confronto: use evidence_role="confronto" nos itens cujo status vem do
  material de confronto e inclua turnos kind="confronto" (role="confronto") que mostrem o que
  ele diz. Se o material de confronto for fraco (sem fonte, só opinião), diga isso no diálogo
  em vez de tratá-lo como prova.
- O veredito é a conclusão DESTE episódio, com base no que foi apresentado ("com base no que
  temos aqui…"); nunca uma sentença absoluta.
- Turnos kind="citacao" e kind="confronto" sempre têm "role". Citação literal = texto copiado
  exatamente da fonte indicada em "role".
- Conteúdo que incite violência, discriminação ou envolva menores de forma imprópria: não
  escreva roteiro; responda apenas {"refused": true}.
"""

SCHEMA = """\
SCHEMA DE SAÍDA (JSON):
{
  "title": string (até 90 caracteres),
  "summary": string (até 280 caracteres),
  "hosts": {"HOST_1": string, "HOST_2": string},
  "turns": [{
    "speaker": "HOST_1" | "HOST_2",
    "text": string (1–600 caracteres),
    "kind": "contexto" | "citacao" | "confronto" | "opiniao" | "pergunta" | "transicao",
    "role": "primaria" | "confronto"   (obrigatório se kind é "citacao" ou "confronto"),
    "source_ts": "mm:ss" | "h:mm:ss"   (obrigatório em "citacao" se a fonte tem timestamps)
  }],
  "verification": [{                   (3 a 8 itens)
    "claim": string (paráfrase da afirmação da fonte primária, até 220 caracteres),
    "claim_ts": "mm:ss" (opcional, se a fonte primária tem timestamps),
    "status": "apoiada" | "contestada" | "parcial" | "nao_verificavel",
    "note": string (motivo do status, até 280 caracteres, nunca vazio),
    "evidence_role": "confronto" | "interna"
  }],
  "verdict": string (até 300 caracteres),
  "fidelity_notes": []
}
"""

TONE_DESC: dict[str, str] = {
    "descontraido": "descontraído e leve, com bom humor, sem perder o rigor",
    "analitico": "analítico, calmo e preciso",
    "provocativo": "provocativo, mas respeitoso: questiona com firmeza, sem atacar pessoas",
}

# §4.3 — mode base (system).
MODE_BASE = """\
Você é roteirista de podcast em português do Brasil. Escreve diálogos naturais entre
dois apresentadores, {host1} (HOST_1) e {host2} (HOST_2), sobre a análise que você já
fez seguindo o PROTOCOLO DE EXAME acima. O roteiro é a dramatização dessa análise —
não um texto novo e desconectado dela.

ESTILO:
- Tom: {tone_desc}. Português falado, frases curtas, interjeições leves ("pois é",
  "calma lá", "exato") sem exagero. Nada de texto de redação.
- Cada fala com no máximo 600 caracteres. Alternar os falantes.
- Escreva números e siglas como se lê em voz alta (ex.: "dois mil e vinte e seis", "I A").
- Sem emojis, sem marcações de cena, sem rubricas.
- Duração alvo: {words} palavras no total (±20%): NUNCA menos de {min_words} palavras.
  Isso dá cerca de {turns} falas de 30 a 60 palavras; desenvolva cada ponto da verificação
  com exemplos e perguntas entre os apresentadores, sem encher linguiça.

SAÍDA: apenas JSON válido no schema fornecido (inclui turns, verification, verdict).
"""

# §4.4
CRITICA_USER = '''\
MODO: CRÍTICA
TESE DO USUÁRIO (linha mestra; trate como opinião do podcast, não como fato):
"""{thesis}"""

ESTRUTURA SUGERIDA:
1. Abertura: apresentar a(s) fonte(s) e seus autores (HOST_1).
2. Resumo fiel dos 2–4 pontos centrais da fonte primária, com no máximo 3 citações
   curtas dela (HOST_1).
3. A crítica: HOST_2 desenvolve a tese do usuário, ponto a ponto, usando o resultado
   do protocolo de exame (confronto ou consistência interna) como evidência — não
   repetindo a tese sem apoio.
4. Contraponto: HOST_1 apresenta o melhor argumento a favor da fonte primária; HOST_2
   responde com base no que foi verificado.
5. Fechamento: o veredito do protocolo de exame, em linguagem de podcast, e o que o
   ouvinte deve verificar por conta própria.

{sources_block}'''

# §4.5
REACT_USER = """\
MODO: REACT (opinião própria, construída pelo protocolo de exame, sem tese prévia do usuário)
{focus_points_block}

ESTRUTURA SUGERIDA:
1. Abertura: o que é a fonte primária e por que vale (ou não) a atenção (HOST_1).
2. O que se sustenta: pontos da fonte primária marcados "apoiada" ou "parcial" na
   verificação, com a evidência que os sustenta.
3. O que não se sustenta: pontos marcados "contestada", com o que o confronto (ou o
   exame interno) revelou.
4. O que ficou em aberto: pontos "nao_verificavel" e por quê.
5. Veredito honesto e proporcional — nem elogio nem demolição automáticos; sem exagero
   positivo nem negativo.

{sources_block}"""

SOURCES_BLOCK = '''\
FONTE PRIMÁRIA{primary_meta} (formato "[mm:ss] texto" quando há timestamps):
"""{material_primario}"""

MATERIAL DE CONFRONTO{confronto_meta} (ausente se vazio — nesse caso, use exame de consistência \
interna):
"""{material_confronto}"""'''

SUMMARIZE_SYSTEM = """\
Você condensa trechos de material para análise posterior. Preserve fielmente as afirmações
centrais, números, nomes e conclusões. Mantenha os marcadores "[mm:ss]" de onde cada
afirmação aparece e copie literalmente (entre aspas) as 2 ou 3 frases mais importantes.
Não opine, não acrescente nada que não esteja no trecho. Responda em texto simples, em pt-BR.
"""


def build_system(hosts: tuple[str, str], tone: Tone, words: int) -> str:
    """Master prompt + internal exam + extra rules + schema + mode base."""
    mode_base = MODE_BASE.format(
        host1=hosts[0],
        host2=hosts[1],
        tone_desc=TONE_DESC.get(tone, TONE_DESC["analitico"]),
        words=words,
        min_words=int(words * 0.85),
        turns=max(8, round(words / 42)),
    )
    return "\n".join([MASTER_PROMPT, INTERNAL_EXAM, EXTRA_RULES, SCHEMA, mode_base])


def _meta(title: str | None, author: str | None, url: str | None) -> str:
    bits = [b for b in (title and f'"{title}"', author and f"de {author}", url) if b]
    return f" ({', '.join(bits)})" if bits else ""


def build_user(
    mode: Mode,
    material_primario: str,
    material_confronto: str,
    thesis: str | None = None,
    focus_points: str | None = None,
    instructions: str | None = None,
    primary_meta: tuple[str | None, str | None, str | None] = (None, None, None),
    confronto_meta: tuple[str | None, str | None, str | None] = (None, None, None),
) -> str:
    sources = SOURCES_BLOCK.format(
        primary_meta=_meta(*primary_meta),
        material_primario=material_primario,
        confronto_meta=_meta(*confronto_meta) if material_confronto else "",
        material_confronto=material_confronto,
    )
    if mode == "critica":
        prompt = CRITICA_USER.format(thesis=(thesis or "").strip(), sources_block=sources)
    else:
        focus = (focus_points or "").strip()
        block = f'PONTOS DE ATENÇÃO DO USUÁRIO:\n"""{focus}"""' if focus else ""
        prompt = REACT_USER.format(focus_points_block=block, sources_block=sources)
    if instructions and instructions.strip():
        # §4.6 — appended at the end; never relaxes the master prompt.
        prompt += f'\n\nAJUSTES PEDIDOS PELO USUÁRIO:\n"""{instructions.strip()}"""'
    return prompt


def build_repair(previous_output: str, errors: list[str]) -> str:
    listed = "\n".join(f"- {e}" for e in errors)
    return (
        "\n\nSUA RESPOSTA ANTERIOR FOI REJEITADA pelo validador pelos motivos abaixo. "
        "Corrija TODOS eles e devolva o JSON completo, seguindo o protocolo e o schema:\n"
        f"{listed}\n\nRESPOSTA ANTERIOR:\n{previous_output[:20000]}"
    )


def build_summarize_user(role_label: str, chunk: str) -> str:
    return f'TRECHO DA {role_label}:\n"""{chunk}"""\n\nCondense este trecho.'
