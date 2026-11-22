# 03 — Contrato da API

Base: `VITE_API_URL` (ex.: `https://contraponto-api.onrender.com`). Prefixo `/api`. Tudo em JSON, exceto onde indicado.
Backend e frontend **devem** bater com este documento; se mudar um, mude o outro e este arquivo no mesmo commit.

## 1. Tipos

```ts
type Mode = "critica" | "react";
type Tone = "descontraido" | "analitico" | "provocativo";
type Status =
  | "created" | "ingesting" | "scripting" | "script_ready"
  | "rendering" | "ready" | "failed";
type SourceRole = "primaria" | "confronto";
type VerificationStatus = "apoiada" | "contestada" | "parcial" | "nao_verificavel";

interface Turn {
  speaker: "HOST_1" | "HOST_2";
  text: string;                 // 1–600 caracteres
  kind: "contexto" | "citacao" | "confronto" | "opiniao" | "pergunta" | "transicao";
  role?: SourceRole;             // obrigatório se kind === "citacao" ou "confronto": de qual fonte vem
  source_ts?: string;            // "mm:ss" ou "h:mm:ss", obrigatório se kind === "citacao" e a fonte tiver timestamps
}

interface VerificationItem {
  claim: string;                 // paráfrase de uma afirmação central da fonte primária (≤220 caracteres)
  claim_ts?: string;             // timestamp da afirmação na fonte primária, se houver
  status: VerificationStatus;
  note: string;                  // por que esse status: o que o confronto diz, ou qual é a lacuna/consistência interna (≤280 caracteres)
  evidence_role: SourceRole | "interna";   // "confronto" = veio do material de confronto; "interna" = exame de consistência interna (sem 2ª fonte)
}

interface Script {
  title: string;                 // até 90 caracteres
  summary: string;               // até 280 caracteres (usado no compartilhamento)
  hosts: { HOST_1: string; HOST_2: string };   // nomes
  turns: Turn[];
  verification: VerificationItem[];   // 3–8 itens, obrigatório em todo roteiro
  verdict: string;               // veredito final, até 300 caracteres
  fidelity_notes: string[];      // avisos do verificador de citações (ex.: "citação não encontrada na fonte primária")
}

interface Source {
  role: SourceRole;
  kind: "youtube" | "text" | "file";
  title?: string;
  author?: string;
  url?: string;
  has_timestamps: boolean;
  char_count: number;
}

interface Episode {
  id: string;
  status: Status;
  mode: Mode;
  created_at: string;            // ISO
  expires_at: string;            // ISO
  sources: Source[];              // 1 item (só primária) ou 2 (primária + confronto)
  script?: Script;
  audio?: { url: string; duration_s: number; bytes: number };
  share_url?: string;             // https://.../s/{id}
  error?: { code: string; message: string };
}
```

## 2. Endpoints

### `GET /api/health`
`200 { "ok": true, "version": "1.0.0", "llm": "gemini|groq|mock", "tts": "edge|piper|mock" }`

### `POST /api/episodes` — cria e inicia ingest + roteiro
`multipart/form-data`:

| Campo | Tipo | Obrigatório | Notas |
|---|---|---|---|
| `mode` | `critica`\|`react` | sim | |
| `youtube_url` | string | um dos três (fonte primária) | |
| `text` | string | um dos três (fonte primária) | até 60 000 caracteres |
| `file` | arquivo | um dos três (fonte primária) | `.txt` `.srt` `.pdf`, até 5 MB |
| `confronto_youtube_url` | string | não | material de confronto, mesmo limite que `youtube_url` |
| `confronto_text` | string | não | até 60 000 caracteres |
| `confronto_file` | arquivo | não | `.txt` `.srt` `.pdf`, até 5 MB |
| `thesis` | string | se `critica` | 1–2 000 caracteres |
| `focus_points` | string | não | só `react` |
| `duration_min` | 3\|5\|8\|12 | não | padrão 5 |
| `tone` | Tone | não | padrão `analitico` |
| `host1_name`, `host2_name` | string | não | padrão "Davi", "Lia" |

Regras de validação:
- Exatamente **um** campo de fonte primária (`youtube_url`, `text` ou `file`) deve vir preenchido.
- **No máximo um** campo de confronto (`confronto_youtube_url`, `confronto_text` ou `confronto_file`); os três são opcionais e mutuamente exclusivos entre si.
- Se nenhum campo de confronto vier preenchido, o roteiro usa exame de consistência interna (ver `docs/04 §3.4`) — isso é um caminho normal, não um erro.

Se `youtube_url` (ou `confronto_youtube_url`) e a transcrição falhar, o episódio vai a `failed` com `error.code = "TRANSCRIPT_UNAVAILABLE"` (ou `CONFRONTO_TRANSCRIPT_UNAVAILABLE`) e a UI oferece colar texto no campo correspondente (reenviando um novo `POST`).

Header opcional: `X-Gemini-Key`.

`202 { "id": "…", "status": "created" }`
Erros: `400`, `413`, `422`, `429`.

### `GET /api/episodes/{id}` → `Episode`
`404` se expirou ou não existe.

### `GET /api/episodes/{id}/events` — SSE (`text/event-stream`)
Eventos:

```
event: progress
data: {"status":"scripting","step":"Cruzando as informações","pct":55}

event: done
data: {"status":"script_ready"}      // ou "ready"

event: error
data: {"code":"LLM_FAILED","message":"…"}
```
Enviar `: keep-alive` a cada 15 s. O cliente reconecta com `EventSource` e, ao reconectar, deve chamar `GET /api/episodes/{id}` para reconciliar.

### `PUT /api/episodes/{id}/script` — salva edições
Body: `Script`. Valida schema e regras (`≤ 3` citações **por fonte**; `citacao` exige `source_ts` se a fonte tem timestamps e `role` indicando de qual fonte vem; `verification` com 3–8 itens, cada um com `note` preenchida). Só em `script_ready`.
`200 Episode` · `409` se o estado não permite · `422` se inválido.

### `POST /api/episodes/{id}/regenerate`
Body opcional: `{ "instructions": "mais curto, menos jargão" }`. Refaz o roteiro (aplica o prompt mestre de novo, com as instruções extras). Só em `script_ready` ou `failed` com roteiro anterior.
`202`.

### `POST /api/episodes/{id}/render` — aprova e gera áudio
Body opcional: `{ "music": true }`. Só em `script_ready`.
`202 { "status": "rendering" }`.

### `GET /api/episodes/{id}/audio.mp3`
`audio/mpeg`, com suporte a `Range`. Query `?download=1` → `Content-Disposition: attachment; filename="<slug-do-titulo>.mp3"`.

### `GET /api/episodes/{id}/script.md` · `script.json` · `verification.md` · `sources.md`
Downloads. `script.md` = transcrição legível do episódio. `verification.md` = tabela de afirmações × status × nota + veredito. `sources.md` = fontes (primária e confronto) e créditos (ver `docs/08`).

### `DELETE /api/episodes/{id}`
`204`. Apaga arquivos.

### `GET /s/{id}` — página pública (HTML, fora de `/api`)
Player `<audio>`, título, resumo, nomes dos apresentadores, veredito curto, aviso "vozes sintéticas", link para a fonte primária (e para a de confronto, se houver), metadados `og:title`, `og:description`, `og:type=music.song`, `og:audio`. Sem scripts de terceiros. `404` amigável se expirou.

## 3. Mensagens de progresso (pt-BR)

| status | step | pct |
|---|---|---|
| ingesting | Lendo a fonte primária | 10 |
| ingesting | Lendo o material de confronto | 20 |
| ingesting | Organizando o conteúdo | 25 |
| scripting | Cruzando as informações | 40 |
| scripting | Escrevendo o roteiro | 60 |
| scripting | Conferindo as citações e o veredito | 80 |
| script_ready | Roteiro pronto para revisão | 100 |
| rendering | Gravando as vozes (n/total) | 10–85 |
| rendering | Mixando o episódio | 90 |
| ready | Episódio pronto | 100 |

Quando não há material de confronto, a etapa "Lendo o material de confronto" é omitida e "Cruzando as informações" se torna "Examinando a consistência do material".

## 4. Códigos de erro

| code | HTTP/estado | Mensagem pt-BR (modelo) |
|---|---|---|
| `INVALID_URL` | 400 | Esse link não parece ser do YouTube. |
| `TRANSCRIPT_UNAVAILABLE` | failed | Não consegui ler a transcrição da fonte primária. Cole o texto abaixo para continuar. |
| `CONFRONTO_TRANSCRIPT_UNAVAILABLE` | failed | Não consegui ler a transcrição do material de confronto. Cole o texto ou remova essa fonte. |
| `INPUT_TOO_LONG` | 413 | O material é longo demais. Tente um trecho de até 60 000 caracteres. |
| `FILE_UNSUPPORTED` | 422 | Envie um arquivo .txt, .srt ou .pdf com texto. |
| `PDF_NO_TEXT` | 422 | Esse PDF parece ser uma imagem escaneada. Cole o texto no lugar. |
| `MULTIPLE_CONFRONTO_INPUTS` | 422 | Escolha só uma forma de enviar o material de confronto: link, texto ou arquivo. |
| `LLM_FAILED` | failed | A IA não respondeu direito. Tente de novo em instantes. |
| `LLM_QUOTA` | failed | O limite gratuito da IA acabou por agora. Tente mais tarde ou use sua própria chave. |
| `SCRIPT_INVALID` | failed | O roteiro saiu fora do formato. Vou tentar de novo. |
| `CONTENT_REFUSED` | failed | Não posso criar um episódio com esse material. Tente outro conteúdo. |
| `TTS_FAILED` | failed | Não consegui gerar as vozes agora. Tente de novo. |
| `RATE_LIMITED` | 429 | Muitos pedidos. Espere um minuto. |
| `EXPIRED` | 404 | Esse episódio expirou. |

Formato de erro HTTP: `{ "error": { "code": "…", "message": "…" } }`.

## 5. Cliente (`apps/web/src/api/client.ts`)

- Funções tipadas: `health()`, `createEpisode(form)`, `getEpisode(id)`, `watchEpisode(id, onEvent)`, `saveScript(id, script)`, `regenerate(id, instr?)`, `render(id, opts?)`, `audioUrl(id, download?)`, `deleteEpisode(id)`.
- `createEpisode(form)` aceita os campos de confronto como opcionais; o `FormData` só inclui o que o usuário preencheu.
- Timeout padrão 30 s; `health()` com 90 s e aviso "Acordando o estúdio…".
- Tipos de `types.ts` espelham a seção 1 (mantê-los idênticos), incluindo `VerificationItem` e `SourceRole`.
