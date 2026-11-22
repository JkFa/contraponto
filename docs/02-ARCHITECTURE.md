# 02 — Arquitetura

## 1. Visão geral

```
┌─────────────────────────┐        HTTPS (CORS restrito)       ┌──────────────────────────────┐
│  apps/web (GitHub Pages)│ ─────────────────────────────────▶ │ apps/api (Render, Docker)    │
│  React + Vite + TS      │ ◀───── JSON + SSE + MP3 ────────── │ FastAPI + FFmpeg             │
└─────────────────────────┘                                    └───────┬──────────────────────┘
                                                                       │
                      ┌───────────────┬───────────────┬────────────────┼───────────────┐
                      ▼               ▼               ▼                ▼               ▼
              youtube-transcript   Gemini API     Groq API         edge-tts          FFmpeg
                -api (×2 fontes)   (principal:     (fallback)     (→ Piper fallback)   + pydub
                                   prompt mestre +
                                   prompt do modo)
```

- O **frontend** é estático. Nenhuma chave secreta vive nele.
- O **backend** guarda as chaves (secrets do Space), ingere **até duas fontes** (primária e confronto), roteiriza com o **prompt mestre** sempre ativo, sintetiza e mixa.
- **Modo local:** `make dev` roda tudo na máquina do usuário (onde o YouTube não bloqueia).

## 2. Estrutura de pastas

```
contraponto/
├── CLAUDE.md
├── README.md
├── CREDITS.md
├── Makefile
├── .env.example
├── .gitignore
├── .github/workflows/
│   ├── ci.yml                 # lint + test em PR/push
│   └── deploy-web.yml         # build e publica no GitHub Pages
├── docs/                      # esta documentação
├── apps/
│   ├── web/
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── vite.config.ts     # base: '/contraponto/'
│   │   └── src/
│   │       ├── main.tsx
│   │       ├── brand.ts       # nome, slogan (único lugar)
│   │       ├── api/           # client.ts (fetch + SSE), types.ts
│   │       ├── routes/        # Home, Review, Episode, History
│   │       ├── components/    # Composer, ConfrontoInput, ModeSwitch, ProgressStudio,
│   │       │                  # ScriptEditor, VerificationPanel, Player, ShareMenu, SourceChips, Toast
│   │       ├── styles/        # tokens.css, base.css, motion.css
│   │       └── lib/           # share.ts, storage.ts, format.ts
│   └── api/
│       ├── Dockerfile
│       ├── README.md          # front-matter do Hugging Face Space
│       ├── requirements.txt
│       ├── pyproject.toml     # ruff + pytest
│       ├── app/
│       │   ├── main.py        # FastAPI, CORS, rate limit, rotas
│       │   ├── config.py      # env (pydantic-settings)
│       │   ├── models.py      # schemas Pydantic (Source, Script, Turn, VerificationItem, Job…)
│       │   ├── jobs.py        # fila em memória, estados, SSE, TTL
│       │   ├── ingest/
│       │   │   ├── youtube.py     # transcrição com timestamps (reusado para as 2 fontes)
│       │   │   ├── files.py       # .txt/.srt/.pdf → texto (reusado para as 2 fontes)
│       │   │   └── normalize.py   # limpeza, chunking
│       │   ├── llm/
│       │   │   ├── base.py        # interface LLM
│       │   │   ├── gemini.py
│       │   │   ├── groq.py
│       │   │   ├── mock.py
│       │   │   └── prompts.py     # prompt mestre + prompts de modo (crítica/react)
│       │   ├── script_service.py  # gera/valida/repara roteiro + verificação
│       │   ├── verification.py    # cruza afirmações da fonte primária com o confronto
│       │   ├── tts/
│       │   │   ├── edge.py
│       │   │   ├── piper.py       # opcional
│       │   │   └── mock.py
│       │   ├── mix.py             # pydub + ffmpeg, loudnorm
│       │   ├── share_page.py      # HTML de /s/{id}
│       │   └── storage.py         # disco temporário + TTL
│       └── tests/
└── assets/
    └── music/                 # só faixas CC0, registradas em CREDITS.md
```

## 3. Máquina de estados do episódio

```
created → ingesting → scripting → script_ready ──(usuário aprova)──▶ rendering → ready
              │            │            │                                │
              └────────────┴────────────┴────────── failed ◀─────────────┘
```

- `ingesting` cobre **as duas fontes** quando há material de confronto (ingestão em paralelo).
- `scripting` cobre extração de afirmações + confronto/exame + geração do roteiro + verificação de citações.
- `script_ready` é o **portão de revisão**: o job fica parado até `POST /render`. É aqui que o usuário vê o painel de verificação.
- `failed` guarda `error_code` e `error_message_pt` (ver `docs/03-API.md §4`).
- Episódios expiram em **24 h** (`expires_at`). Limpeza por tarefa periódica.

## 4. Fluxo de dados

1. `POST /api/episodes` cria o episódio com a fonte primária e, se enviado, o material de confronto; dispara **ingest + roteiro (com o prompt mestre)** em background.
2. O front abre `GET /api/episodes/{id}/events` (SSE) e mostra o progresso, incluindo "Cruzando as informações".
3. Ao chegar em `script_ready`, o front busca `GET /api/episodes/{id}` (traz o roteiro + `verification` + `verdict`) e abre a Revisão.
4. `PUT /api/episodes/{id}/script` salva edições (falas e itens de verificação). `POST /api/episodes/{id}/regenerate` refaz o roteiro.
5. `POST /api/episodes/{id}/render` dispara TTS + mixagem; SSE continua até `ready`.
6. `GET /api/episodes/{id}/audio.mp3` serve o áudio (com `Content-Disposition` para download).
7. `GET /s/{id}` é a página pública de compartilhamento.

## 5. Concorrência e limites

- Fila em memória com **no máximo 2 jobs de render simultâneos** (CPU gratuita é pequena).
- Rate limit: **10 req/min** por IP em rotas de criação; **3 episódios/hora** por IP.
- Limites de entrada em `docs/01-PRD.md §3` — valem para **cada** fonte (primária e confronto) separadamente.
- Timeout do LLM: 90 s, com 2 retries (backoff 2 s, 6 s). A chamada de roteiro é uma só (recebe as duas fontes já normalizadas no mesmo prompt), não duas chamadas separadas.

## 6. Segurança

- **CORS:** `ALLOWED_ORIGINS` só com a origem do GitHub Pages e `http://localhost:5173`.
- **SSRF:** aceitar apenas URLs cujo host seja `youtube.com`, `www.youtube.com`, `m.youtube.com`, `youtu.be`. Extrair `video_id` por regex; nunca fazer `fetch` de URL arbitrária. Regra idêntica para a URL de confronto.
- **Uploads:** validar extensão e tipo; ler em memória/temp; limitar tamanho; nunca executar conteúdo. Vale para os dois uploads possíveis.
- **Chaves:** só no backend (env). BYOK vem em header `X-Gemini-Key`, usada na requisição e **nunca** logada nem persistida.
- **Logs:** sem conteúdo de usuário (só ids, estados, durações, códigos de erro) — nem da fonte primária nem do confronto.
- **HTML de compartilhamento:** escapar todo texto (título, nomes) antes de renderizar.
- **IDs:** `secrets.token_urlsafe(9)` (não sequenciais).

## 7. Variáveis de ambiente

Ver `.env.example` em `docs/06-DEPLOY.md §5`.

## 8. Por que essa divisão

- **GitHub Pages** não executa Python/FFmpeg → backend separado é necessário.
- **Render (Docker, plano free)** aceita FFmpeg e Python e expõe HTTPS. (Era o Hugging Face Space, que desde 22/11/2026 exige PRO para Docker.)
- Se o Space dormir (inatividade), a primeira chamada acorda em ~30–60 s: a UI deve mostrar "Acordando o estúdio…" quando `GET /api/health` demorar.
- A ingestão é **genérica por papel** (`role: "primaria" | "confronto"`), não duplicada em código: o mesmo módulo `ingest/youtube.py` e `ingest/files.py` atende as duas fontes, o que mantém a base de código pequena mesmo com a segunda entrada.
