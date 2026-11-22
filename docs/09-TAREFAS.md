# 09 — Tarefas (milestones)

> Marque `[x]` ao concluir. Ao fim de cada milestone: `make test` + `make lint` → commit → marcar aqui.
> Ordem importa: **mock primeiro**, chaves reais depois.

## M0 — Preparação
- [x] Ler `CLAUDE.md` e todos os `docs/`
- [x] Verificar ferramentas: `python3 --version` (≥ 3.11), `node --version` (≥ 20), `ffmpeg -version`, `gh auth status`
- [x] Instalar o que faltar (`ffmpeg`, dependências) sem pedir confirmação
- [x] Criar estrutura de pastas (`docs/02-ARCHITECTURE.md §2`), `.gitignore`, `.env.example`, `Makefile`, `CREDITS.md`
- [x] `git init -b main` e primeiro commit

## M1 — Backend esqueleto + modo mock
- [x] FastAPI com `GET /api/health`, CORS, config (pydantic-settings), logging sem conteúdo
- [x] Modelos Pydantic (`Source`, `Script`, `Turn`, `VerificationItem`, `Episode`, estados) idênticos a `docs/03-API.md`
- [x] `jobs.py`: fila em memória, máquina de estados, SSE com keep-alive, TTL e limpeza
- [x] Provedores **mock** de LLM (retornando `verification` e `verdict` válidos) e TTS
- [x] Rotas: criar (com e sem confronto), obter, eventos, salvar roteiro, regenerar, render, áudio, downloads (incluindo `verification.md`), delete
- [x] Teste de integração do fluxo completo em mock, com e sem material de confronto
- [x] `make dev`, `make mock`, `make test`, `make lint` funcionando

## M2 — Ingestão (duas fontes)
- [x] `youtube.py` (regex + SSRF + `fetch` v1.x + oEmbed + cache), reusado por `role`
- [x] `files.py` (`.txt`, `.srt`, `.pdf`) e `normalize.py` (limpeza, chunking, map-reduce), reusados por `role`
- [x] Erros `INVALID_URL`, `TRANSCRIPT_UNAVAILABLE`, `CONFRONTO_TRANSCRIPT_UNAVAILABLE`, `FILE_UNSUPPORTED`, `PDF_NO_TEXT`, `INPUT_TOO_LONG`, `MULTIPLE_CONFRONTO_INPUTS`
- [x] Testes unitários (incluindo URLs maliciosas nas duas entradas)

## M3 — Prompt mestre, modos e verificação
- [x] `llm/prompts.py`: prompt mestre fixo (`docs/04 §3.2`) + prompts de modo (`crítica`/`react`, `docs/04 §4.4-4.5`)
- [x] `llm/gemini.py` e `llm/groq.py` com fallback e retries
- [x] `script_service`: gerar, validar (regras de `docs/04 §4.1`, incluindo `verification`/`verdict`), reparar (até 2×)
- [x] `verification.py`: cruza afirmações da fonte primária com o material de confronto, ou aplica o checklist de consistência interna (`docs/04 §3.4`) quando não houver confronto
- [x] Verificador de citações por fonte (`role` correto, limite de 3 por fonte)
- [x] Testes com respostas simuladas: com confronto (apoiada/contestada/parcial), sem confronto (interna), schema inválido, 4 citações de uma fonte, citação com `role` errado
- [x] Se `GEMINI_API_KEY` existir no ambiente: rodar um roteiro real (com e sem confronto) e registrar o resultado. Se não existir: seguir com mock e anotar em `docs/06 §4.4` — **não existia** (21/11/2026); seguiu em mock, anotado

## M4 — Áudio
- [x] `tts/edge.py` (concorrência 3, retry, `tts_prepare`) — fallback Piper **não implementado** (opcional; ficou no backlog, ver `docs/06 §4.6`)
- [x] `mix.py`: pausas, `loudnorm`, MP3 128 kbps, tags ID3 com selo de voz sintética
- [x] Música opcional **somente** se houver faixa CC0 registrada — nenhuma registrada em `CREDITS.md`, então episódios saem sem música
- [x] Teste: MP3 válido, duração > 0, Range, `Content-Disposition`
- [x] `share_page.py` (`/s/{id}`) com HTML escapado, veredito e Open Graph

## M5 — Frontend (usar a skill `frontend-design`)
- [x] Invocar `frontend-design`; ler `docs/05-DESIGN-UI.md`
- [x] Scaffold Vite + React + TS + `HashRouter`; tokens, tipografia (`@fontsource`), base e motion
- [x] `api/client.ts` + `types.ts` iguais ao contrato (incluindo `VerificationItem`); SSE com reconciliação
- [x] Home: `Composer` (fonte primária), `ConfrontoInput` (opcional, recolhido por padrão), `ModeSwitch`, ajustes, trilho de histórico
- [x] `ProgressStudio` (luz NO AR, etapas incluindo cruzamento/exame interno, "acordando o estúdio", painel "cole o texto" por fonte)
- [x] Revisão: `ScriptEditor`, chips (tipo + fonte), `VerificationPanel` (selos por status + veredito), painel de fidelidade, regenerar, aprovar
- [x] Episódio: `Player` (waveform, atalhos), veredito em destaque, ações (baixar MP3, compartilhar, copiar link, roteiro, verificação, fontes)
- [x] `ShareMenu` + `lib/share.ts` com a ordem de fallback de `docs/05 §6`
- [x] Histórico local e tratamento de expirado
- [x] **Olhar as telas** em 390 px e 1280 px, corrigir, salvar capturas em `docs/screens/`, incluindo `ConfrontoInput` e `VerificationPanel`
- [x] Testes vitest + Playwright (modo mock, com e sem confronto) + axe — Playwright usa o Google Chrome do sistema (`channel: "chrome"`)

## M6 — Integração e endurecimento
- [x] Rate limit, limites de tamanho/duração por fonte, BYOK por header, logs sem conteúdo
- [x] CORS restrito por `ALLOWED_ORIGINS`
- [x] Texto legal e selos (`docs/08 §9`) na UI, em `sources.md`, `verification.md` e na página pública
- [ ] Fluxo completo local com chave real (se disponível), com e sem material de confronto, usando uma fonte primária real — **parcial (22/11/2026):** sem chave de LLM; rodado com YouTube real + edge-tts real + LLM mock, com e sem confronto: MP3 de 2 min 18 s, −16,4 LUFS, ID3 ok. Falta repetir com Gemini real

## M7 — Publicação
- [x] `gh repo create JkFa/contraponto --public --push`
- [x] Workflows `ci.yml` e `deploy-web.yml`; Pages ativado por `gh api` (ambos verdes)
- [x] `apps/api` com Dockerfile e front-matter; `scripts/deploy_space.sh`; `make deploy-api` (imagem testada localmente)
- [x] Publicar o Space (se `hf auth` estiver feito) ou deixar pronto e documentar — HF passou a exigir PRO para Docker (402); backend migrado para **Render** (`render.yaml`, imagem testada com `PORT=10000`); criação do serviço é passo do usuário (`docs/06 §4R`)
- [ ] Configurar `VITE_API_URL` e redeploy do web — depende da URL do serviço no Render
- [ ] Teste do site publicado: CORS, fluxo completo (com e sem confronto), download e compartilhamento — depende do backend no Render

## M8 — Qualidade final
- [ ] 4 episódios reais avaliados (`docs/07 §3`) → `docs/QUALITY-REPORT.md`
- [ ] Checklist de `docs/07 §5` completo
- [ ] Checklist de `docs/08 §10` completo
- [ ] `README.md` com URLs finais e instruções
- [ ] Entrega ao usuário: URLs + lista curta do que só ele pode fazer

## Backlog (fase 2, **não** fazer antes de M8)
- Audiograma MP4 (`ffmpeg showwaves`) e imagem de capa
- Transcrição sincronizada com o áudio (`turn_offsets`)
- Bot do Telegram
- Mais de uma fonte de confronto por episódio
- Persistência de episódios (ex.: archive.org ou dataset do Hugging Face) com link permanente
- Publicação em podcast host (Spotify for Creators)
- Piper como TTS totalmente local e música de fundo CC0
