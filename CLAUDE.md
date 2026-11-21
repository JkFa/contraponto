# CLAUDE.md — Contraponto

> Leia este arquivo inteiro antes de qualquer ação. Ele é a fonte de verdade para o Claude Code neste repositório.
> **Nome de trabalho: "Contraponto"** (placeholder, pode ser trocado em um único lugar: `apps/web/src/brand.ts` + `README.md`).

## 1. O que é o projeto

Aplicação web que recebe **uma fonte primária** (link do YouTube, texto colado ou arquivo `.txt`/`.srt`/`.pdf`) e, opcionalmente, **um material de confronto** (um segundo texto/arquivo que o usuário fornece para checar, contestar ou verificar o que a fonte primária afirma) e gera um **episódio de podcast em áudio com dois apresentadores sintéticos**.

**O núcleo do produto não é resumir — é examinar.** Toda geração de roteiro passa por um **prompt mestre** (ver `docs/04-PIPELINE-E-PROMPTS.md §3`) que obriga a IA a: **extrair** as afirmações centrais da fonte primária, **confrontá-las** com o material de confronto (quando houver) ou com critérios de consistência interna (quando não houver), **examinar** a força de cada afirmação e **verificar** o que se sustenta, o que é contestado e o que não é verificável — produzindo um **veredito** no fim do episódio. Isso vale nos dois modos (`crítica` e `react`); o modo decide só se a tese condutora é do usuário ou da IA.

- Sem avatar, sem download/edição do vídeo original (evita GPU e Content ID).
- Custo zero: Gemini/Groq free tier, `edge-tts`, FFmpeg, GitHub Pages, Hugging Face Spaces.
- Idioma da interface e dos episódios: **pt-BR**. Código, commits e nomes de arquivos: **inglês**. Documentação: **português**.

Documentos de apoio (leia sob demanda, na ordem):

| Arquivo | Quando ler |
|---|---|
| `docs/01-PRD.md` | Escopo, modos, fonte primária x material de confronto, requisitos, o que NÃO fazer |
| `docs/02-ARCHITECTURE.md` | Estrutura de pastas, stack, fluxo de dados |
| `docs/03-API.md` | Contratos dos endpoints (backend e frontend devem bater com isto) |
| `docs/04-PIPELINE-E-PROMPTS.md` | Ingestão das duas fontes, **prompt mestre de confronto/exame/verificação**, prompts por modo, TTS, mixagem |
| `docs/05-DESIGN-UI.md` | Direção visual, telas (incluindo o painel de verificação), componentes, acessibilidade |
| `docs/06-DEPLOY.md` | GitHub Pages, Hugging Face Space, CI, variáveis |
| `docs/07-TESTES-E-QUALIDADE.md` | Testes, critérios de aceite, checklist final |
| `docs/08-LEGAL-E-ETICA.md` | Guardrails de direitos autorais, fidelidade, transparência (vale para as duas fontes) |
| `docs/09-TAREFAS.md` | Milestones e checklist. **Marque `[x]` ao concluir.** |
| `docs/00-KICKOFF-PROMPT.md` | Prompt de partida (referência) |

## 2. Modo autônomo (instrução permanente)

Execute o projeto **de ponta a ponta sem pedir confirmação** para decisões de rotina: criar pastas, instalar dependências, escrever código, rodar testes, corrigir erros, fazer commits, criar o repositório e configurar o deploy.

**Pare e pergunte somente quando:**
1. Faltar um **segredo** que só o usuário tem (ex.: `GEMINI_API_KEY`, token do Hugging Face). Deixe tudo pronto, documente o passo exato em `docs/06-DEPLOY.md` e continue com o que não depende dele (use o modo `MOCK_LLM=1`).
2. A ação for **irreversível ou destrutiva** (force-push, apagar repositório, sobrescrever arquivo do usuário).
3. A ação puder **violar `docs/08-LEGAL-E-ETICA.md`**.

Ritmo de trabalho:
- Siga `docs/09-TAREFAS.md` milestone por milestone. Ao fim de cada uma: rodar testes → commit → marcar `[x]`.
- Use lista de tarefas (TaskCreate/TaskUpdate) para mostrar o progresso.
- Não narre cada passo. No fim de cada milestone, 2–3 linhas: o que ficou pronto e o que vem a seguir.
- Se um teste falhar, **corrija a causa**; não remova nem enfraqueça o teste.

## 3. Skill de frontend (obrigatório)

O plugin **Frontend Design** já está instalado. **Antes de escrever qualquer UI**, invoque a skill `frontend-design` (via Skill tool) e siga-a junto com `docs/05-DESIGN-UI.md`.

Regras:
- Evite o visual genérico de IA (gradiente roxo, Inter em tudo, cards idênticos, sombras difusas padrão).
- A direção estética está definida em `docs/05-DESIGN-UI.md`. A skill refina a execução (tipografia, composição, movimento); não troca a direção sem motivo registrado.
- Depois de montar cada tela, **abra no navegador e olhe** (viewport 390 px e 1280 px). Corrija o que estiver feio antes de seguir.
- Acessibilidade não é opcional: contraste AA, foco visível, `prefers-reduced-motion`, rótulos em todos os controles.

## 4. Decisões de arquitetura já tomadas (não reabrir sem motivo)

| Decisão | Escolha | Motivo |
|---|---|---|
| Frontend | **GitHub Pages** (SPA estática, deploy por GitHub Actions) | O usuário prefere GitHub, não tem domínio, sem limite de uso não comercial |
| Backend | **FastAPI em Docker no Hugging Face Space** (CPU gratuita) | Precisa de Python + FFmpeg; Vercel/Pages não rodam isso |
| Alternativa de frontend | Vercel (documentada em `docs/06-DEPLOY.md`) | Só se o usuário pedir |
| LLM | Gemini (AI Studio, free tier) → fallback Groq | Contexto longo; JSON estruturado |
| TTS | `edge-tts` → fallback Piper local | Edge-TTS é API não oficial; precisa de plano B |
| Transcrição | `youtube-transcript-api` v1.x (`.fetch()`) → fallback colar transcrição | YouTube costuma bloquear IPs de nuvem |
| **Entradas** | **Duas fontes**: primária (obrigatória) e confronto (opcional), ambas podem ser link do YouTube, texto ou arquivo | O usuário precisa poder trazer um material próprio para checar a fonte primária |
| **Roteiro** | **Prompt mestre** sempre ativo (crítica/confrontação/exame/verificação) + prompt do modo (`crítica` ou `react`) | O produto existe para examinar, não só resumir |
| Roteiro (fluxo) | **Duas fases**: gerar roteiro → revisão humana → renderizar áudio | Evita distorcer o que as fontes afirmam |
| Estado | Em memória + disco temporário, TTL de 24 h | Sem banco, custo zero |

## 5. Convenções

- **Monorepo** (`apps/web`, `apps/api`). Detalhes em `docs/02-ARCHITECTURE.md`.
- **Frontend:** Vite + React 18 + TypeScript estrito, CSS com variáveis (tokens), `HashRouter` (necessário no GitHub Pages). Sem biblioteca de UI pesada.
- **Backend:** Python 3.11, FastAPI, Pydantic v2, `ruff` + `pytest`. Tipagem em todas as funções públicas.
- **Commits:** Conventional Commits em inglês (`feat:`, `fix:`, `docs:`, `chore:`, `test:`). Um commit por unidade lógica.
- **Branch:** trabalhar em `main` direto é aceitável neste projeto solo; use branch para mudanças arriscadas.
- **Segredos:** nunca no repositório. `.env` no `.gitignore`; manter `.env.example` atualizado.
- **Dependências:** fixe versões (`requirements.txt` com `==`, `package-lock.json` commitado). Prefira poucas dependências.
- **Erros ao usuário:** sempre em pt-BR, claros e com a ação sugerida (ex.: "Não consegui ler a transcrição desse vídeo. Cole o texto abaixo.").

## 6. Comandos (devem existir ao fim do Milestone 1)

```bash
make setup      # instala web + api
make dev        # sobe api (:8000) e web (:5173) juntos
make test       # pytest + vitest
make lint       # ruff + eslint + tsc --noEmit
make build      # build de produção do web
make mock       # dev com MOCK_LLM=1 e MOCK_TTS=1 (sem chaves, sem rede)
```

## 7. Definição de pronto (global)

O projeto só está "pronto" quando **todos** os itens de `docs/07-TESTES-E-QUALIDADE.md §5` estiverem marcados: frontend publicado no GitHub Pages, backend no Space, fluxo completo funcionando com uma fonte primária real **e** com um material de confronto real, download do MP3 e compartilhamento testados.

## 8. Nunca fazer

- Baixar, armazenar ou reproduzir áudio/vídeo do YouTube (fonte primária ou de confronto).
- Usar música ou efeitos sem licença registrada em `CREDITS.md`.
- Gerar roteiro com mais de **3 citações literais por fonte** (primária e, se houver, confronto), ou com afirmação sobre qualquer uma das fontes sem respaldo.
- Tratar o material de confronto como automaticamente mais correto que a fonte primária, ou vice-versa — o papel da IA é **confrontar e expor**, não arbitrar quem "ganha".
- Pular o protocolo de confronto/exame/verificação do prompt mestre, mesmo quando não houver material de confronto (nesse caso, aplicar exame de consistência interna — ver `docs/04 §3.4`).
- Publicar chave de API no frontend ou no repositório.
- Dizer que algo "funciona" sem ter rodado.
