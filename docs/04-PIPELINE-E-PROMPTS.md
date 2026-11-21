# 04 — Pipeline, prompts e áudio

## 1. Etapas

```
ingest (primária [+ confronto]) → normalize → (chunk)
   → script: PROMPT MESTRE (confronto/exame/verificação) + prompt do modo (LLM)
   → validate/repair → verify citations (por fonte)
   → [REVISÃO HUMANA] → TTS por fala → mix → loudnorm → MP3
```

A diferença central deste produto para um resumidor comum está na etapa "script": o LLM nunca recebe só "resuma isto". Ele sempre recebe o **prompt mestre** (seção 3) empilhado com o **prompt do modo** (seção 4). O prompt mestre é o que não muda; o prompt do modo é o que decide se a tese condutora é do usuário (`crítica`) ou da própria IA (`react`).

## 2. Ingestão

A ingestão é **idêntica para as duas fontes** (primária e confronto) — o mesmo código roda duas vezes, uma por `role`, quando há confronto.

### YouTube (`ingest/youtube.py`)
- Extrair `video_id` por regex de `youtube.com/watch?v=`, `youtu.be/`, `/shorts/`, `/embed/`. Rejeitar o resto (`INVALID_URL`).
- Transcrição com a API **v1.x** (o método estático `get_transcript` foi removido):

```python
from youtube_transcript_api import YouTubeTranscriptApi

def fetch_transcript(video_id: str) -> list[tuple[int, str]]:
    ytt = YouTubeTranscriptApi()
    snippets = ytt.fetch(video_id, languages=["pt", "pt-BR", "en"])
    return [(int(s.start), s.text.replace("\n", " ").strip()) for s in snippets]
```

- Título e autor: `oEmbed` (`https://www.youtube.com/oembed?url=…&format=json`) — só leitura de metadados públicos; se falhar, seguir sem eles.
- Em qualquer exceção da transcrição → `TRANSCRIPT_UNAVAILABLE` (fonte primária) ou `CONFRONTO_TRANSCRIPT_UNAVAILABLE` (confronto); a UI oferece colar o texto no campo correspondente.
- Cache em disco por `video_id` (TTL 24 h) para não repetir chamada.
- Formatar como linhas `[mm:ss] texto` para o LLM poder citar timestamps.

### Texto e arquivos (`ingest/files.py`)
- `.txt`: UTF-8 (tentar `latin-1` se falhar).
- `.srt`: extrair blocos, manter início como timestamp.
- `.pdf`: `pypdf` extrai texto; se vier quase vazio → `PDF_NO_TEXT`.
- Texto colado: sem timestamps (`has_timestamps = false`).

### Normalização (`ingest/normalize.py`)
- Remover repetições de legenda automática, `[Música]`, `[Aplausos]`, espaços duplicados.
- Estimar tokens (`chars / 3.6`). Se a **soma** das duas fontes passar de **~900 mil tokens** (Gemini) ou **~90 mil** (Groq), usar **map-reduce**: resumir blocos de ~12 mil tokens preservando timestamps e depois gerar o roteiro sobre os resumos + trechos-chave. O material de confronto nunca é cortado antes da fonte primária — se precisar reduzir, reduza as duas proporcionalmente.
- Resultado final da ingestão: `material_primario` (string formatada `[mm:ss] texto`) e, se houver, `material_confronto` (mesmo formato), prontos para entrar no prompt.

## 3. O prompt mestre (sempre ativo)

### 3.1 Papel do prompt mestre

O prompt mestre é um bloco de instruções de sistema **fixo**, enviado em toda chamada de geração/regeneração de roteiro, antes do prompt do modo. Ele obriga a IA a executar quatro operações, nesta ordem, para o próprio raciocínio (o que aparece no roteiro final é o resultado, não o processo passo a passo):

1. **Extrair**: listar as 3 a 8 afirmações centrais da fonte primária (fatos, dados, conclusões — não detalhes menores).
2. **Confrontar**: para cada afirmação, verificar se o material de confronto apoia, contesta, apoia parcialmente ou não toca nela. Sem material de confronto: aplicar exame de consistência interna (seção 3.4).
3. **Examinar**: avaliar a força de cada afirmação por si só — tem dado/fonte citada? é generalização? é opinião apresentada como fato?
4. **Verificar**: converter o resultado das três etapas acima no campo `verification` (schema em `docs/03-API.md`) e fechar com um `verdict` curto.

O roteiro (os `turns`) é a dramatização dessa análise em diálogo — não um texto corrido separado dela. Toda vez que o diálogo afirma algo sobre a fonte primária, isso deve corresponder a um item em `verification`.

### 3.2 Texto do prompt mestre (system, parte fixa)

```text
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
```

### 3.3 Por que não arbitrar

O prompt mestre proíbe explicitamente a IA de tratar o material de confronto como "fonte da verdade" só porque o usuário o trouxe para checar a outra. O papel do produto é **expor** a contradição ou a convergência com transparência (o que cada lado diz, com que base) — quem está mais correto, se alguém estiver, deve ficar claro pelo peso dos dados mostrados aos ouvintes, não por uma hierarquia prévia entre as fontes.

### 3.4 Exame de consistência interna (sem material de confronto)

Quando não há material de confronto, a etapa "confrontar" do protocolo é substituída por este checklist, aplicado à própria fonte primária:

- A afirmação cita um dado, estudo ou fonte, ou é uma afirmação solta?
- A afirmação generaliza (ex.: "todo mundo", "sempre", "nunca") sem suporte?
- Há contradição entre partes diferentes do próprio material?
- A conclusão segue logicamente das premissas apresentadas, ou há salto?
- Falta contexto que mudaria o sentido da afirmação?

Cada item de `verification` nesse caso usa `evidence_role: "interna"` e a `note` explica qual critério do checklist motivou o status (por exemplo: `"Generalização sem dado que a sustente"`).

## 4. Prompt do modo (empilhado sobre o prompt mestre)

### 4.1 Schema de saída (igual a `Script` em `docs/03-API.md`)
Validar com Pydantic. Regras extras do validador:

1. `turns` entre `N_min` e `N_max`, onde ~ **150 palavras ≈ 1 min** de fala em pt-BR (alvo = `duration_min × 150` palavras, tolerância ±20%).
2. No máximo **3** turnos `kind="citacao"` **por fonte** (`role="primaria"` e `role="confronto"` contados separadamente); cada um com **≤ 15 palavras** e `source_ts` (se a fonte tem timestamps).
3. `verification` com **3 a 8 itens**; cada item com `note` não vazia; se `evidence_role != "interna"`, deve haver pelo menos um turno `kind="confronto"` relacionado no roteiro.
4. `verdict` preenchido, até 300 caracteres.
5. Falantes alternam com naturalidade (nunca mais de 2 turnos seguidos do mesmo).
6. Nenhum turno > 600 caracteres.
7. Primeiro turno apresenta o tema e a(s) fonte(s) (com nome do autor/canal quando houver); último turno encerra com o veredito resumido.
8. Em `critica`: a tese do usuário aparece como linha mestra e é marcada como opinião ("na nossa avaliação…", "a crítica aqui é…"), mas o protocolo de verificação continua valendo igual.

Se falhar: **repara** reenviando o erro de validação ao LLM (até 2 vezes, com o prompt mestre + prompt do modo intactos). Depois disso, `SCRIPT_INVALID`.

### 4.2 Verificador de citações (`script_service.verify_citations`)
Para cada `citacao`: procurar o trecho (normalizado: minúsculas, sem pontuação) **na fonte indicada por `role`** (nunca na outra). Se não achar com similaridade ≥ 0.85 (`rapidfuzz`), adicionar a `fidelity_notes`: `"Citação do turno N (fonte {role}) não encontrada — confira."` e **destacar na UI** da revisão. Não bloquear: o humano decide.

### 4.3 Prompt de sistema do modo — base comum

```text
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
- Duração alvo: {words} palavras no total (±20%).

SAÍDA: apenas JSON válido no schema fornecido (inclui turns, verification, verdict).
```

### 4.4 Prompt de usuário — modo `critica`

```text
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

FONTE PRIMÁRIA (formato "[mm:ss] texto" quando há timestamps):
"""{material_primario}"""

MATERIAL DE CONFRONTO (ausente se vazio — nesse caso, use exame de consistência interna):
"""{material_confronto}"""
```

### 4.5 Prompt de usuário — modo `react`

```text
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

FONTE PRIMÁRIA:
"""{material_primario}"""

MATERIAL DE CONFRONTO (ausente se vazio — nesse caso, use exame de consistência interna):
"""{material_confronto}"""
```

### 4.6 Regeneração
`instructions` do usuário entram como bloco `AJUSTES PEDIDOS PELO USUÁRIO:` ao final do prompt do modo, sem relaxar o prompt mestre nem as regras de fidelidade — regenerar nunca remove a verificação.

## 5. Síntese de voz (`tts/`)

- **Vozes padrão (edge-tts):** `HOST_1 = pt-BR-AntonioNeural`, `HOST_2 = pt-BR-FranciscaNeural`. Configuráveis por env.
- Uma chamada por turno; limite de concorrência 3; retry 2× com backoff.
- Rate/pitch levemente diferentes por apresentador para evitar monotonia (ex.: `+0%`/`+0Hz` e `+3%`/`+2Hz`).
- Texto enviado ao TTS passa por `tts_prepare()`: remove markdown, expande `%` → "por cento", `R$ 10` → "dez reais", normaliza siglas.
- **Fallback Piper** (`TTS_PROVIDER=piper`): modelo pt-BR local baixado no build do Docker. Só ativar se o Edge falhar 3× seguidas.
- **Mock** (`MOCK_TTS=1`): gera tom/silêncio curto por turno com FFmpeg (`anullsrc`/`sine`), suficiente para testar mixagem e player.

## 6. Mixagem (`mix.py`)

1. Concatenar turnos com **pausa de 250–400 ms** (mais longa após `pergunta`, `transicao` e troca entre `citacao`/`confronto` de fontes diferentes; `random` com seed fixa por episódio para ser reprodutível).
2. Opcional: **bed** musical CC0 em −22 dB com *ducking* simples (reduzir quando há voz) e fade in/out de 1,5 s; **sem música no MVP se não houver faixa CC0 registrada em `CREDITS.md`**.
3. Normalizar loudness: `ffmpeg -af loudnorm=I=-16:TP=-1.5:LRA=11`.
4. Exportar MP3 **128 kbps mono/44.1 kHz** (`-codec:a libmp3lame -b:a 128k`), com tags ID3: título, artista = "Contraponto (vozes sintéticas)", comentário = URL da fonte primária.
5. Calcular `duration_s` e `bytes` e gravar no episódio.

## 7. Artefatos de saída

- `episode.mp3`
- `script.json` (schema `Script`, inclui `verification` e `verdict`)
- `script.md` — transcrição do episódio, uma fala por parágrafo, com nome do apresentador, marcador de citações e de qual fonte (primária/confronto) cada citação vem.
- `verification.md`:

```markdown
# Verificação
| Afirmação | Status | Nota |
|---|---|---|
| {claim} | {status} | {note} |

**Veredito:** {verdict}
```

- `sources.md`:

```markdown
# Fontes e créditos
- Fonte primária: **{título}** — {autor/canal} — {url} (acessado em {data})
- Material de confronto: **{título}** — {autor/canal} — {url} (acessado em {data})  <!-- omitir se não usado -->
- Este episódio é um exame crítico gerado com apoio de IA, que confronta as fontes
  acima (ou aplica exame de consistência interna, se só houver uma). As vozes são sintéticas.
- Citações literais (máx. 3 por fonte) com timestamp: …
- Modelo de linguagem: {llm}. Vozes: {tts}.
- Música: {faixa, autor, licença} (ou "sem música")
```

## 8. Descrição sugerida para publicação (texto pronto no `sources.md`)

> Episódio gerado com IA (vozes sintéticas) examinando "{título}" de {autor} ({url}), confrontado com {título do material de confronto, ou "exame de consistência interna"}. As conclusões são do episódio e podem divergir das fontes originais.
