# Contraponto

Gere um episódio de podcast com **duas vozes** que **examina, confronta e verifica** as informações de um vídeo, texto ou arquivo — comparando-as, se você quiser, com um material próprio que você fornece. Revise o roteiro, baixe o MP3 e compartilhe.

> Nome de trabalho. Custo zero: GitHub Pages + Hugging Face Space + free tiers.

## Endereços

| | URL | Estado |
|---|---|---|
| Frontend | https://jkfa.github.io/contraponto/ | publicado (GitHub Pages) |
| Backend | `https://<usuario-hf>-contraponto.hf.space` | pronto para publicar: `make deploy-api` (precisa de login no Hugging Face) |
| Repositório | https://github.com/JkFa/contraponto | público |

Enquanto o backend não estiver publicado e ligado ao site (`VITE_API_URL`), a página publicada avisa que o estúdio
ainda não está conectado. Localmente tudo funciona com `make mock` (sem chaves) ou `make dev` (com chave).

### Para colocar no ar (passos do dono do projeto)

1. `hf auth login` (token com permissão de escrita) e `make deploy-api`.
2. No Space → Settings → *Variables and secrets*: secret `GEMINI_API_KEY` (de `aistudio.google.com`), opcional
   `GROQ_API_KEY`; variables `ALLOWED_ORIGINS=https://jkfa.github.io,http://localhost:5173`,
   `PUBLIC_BASE_URL=https://<usuario-hf>-contraponto.hf.space` e `FRONTEND_URL=https://jkfa.github.io/contraponto/`.
3. `gh variable set VITE_API_URL --body "https://<usuario-hf>-contraponto.hf.space" --repo JkFa/contraponto`
   e `gh workflow run deploy-web.yml --repo JkFa/contraponto`.

## Como funciona

1. **Fonte primária** (obrigatória): cole um **link do YouTube**, um **texto** ou envie um **arquivo** (`.txt`, `.srt`, `.pdf`).
2. **Material de confronto** (opcional): cole um texto, outro link ou envie um arquivo que será usado para **checar, contestar ou confirmar** o que a fonte primária afirma — um artigo divergente, dados oficiais, suas próprias notas, uma segunda fonte.
3. Escolha o modo:
   - **Crítica**: você escreve a tese (tópicos soltos servem) e os apresentadores argumentam com ela, usando o confronto como evidência.
   - **React**: a IA forma a própria opinião, sempre cruzando a fonte primária com o confronto (ou com critérios de consistência interna, se não houver confronto).
4. A IA gera o roteiro já aplicando o **protocolo de confrontação/exame/verificação**: para cada afirmação central, diz se está apoiada, contestada ou não verificável — e termina com um veredito curto.
5. **Revise o roteiro** (edite falas, confira citações com timestamp e o painel de verificação).
6. **Gere o áudio** e acompanhe o progresso.
7. **Baixe o MP3**, o roteiro, a tabela de verificação e as fontes, ou **compartilhe** o link do episódio.

## Rodando localmente

```bash
make setup
cp .env.example .env     # preencha GEMINI_API_KEY
make dev                 # web em :5173, api em :8000
make mock                # sem chaves: respostas simuladas
make test && make lint   # pytest + vitest; ruff + eslint + tsc
make e2e                 # Playwright (usa o Google Chrome do sistema)
```

Requisitos: Python 3.11+, Node 20+, FFmpeg.

## Estrutura

```
apps/web    # React + Vite (GitHub Pages)
apps/api    # FastAPI (Hugging Face Space, Docker)
docs/       # PRD, arquitetura, API, prompts, design, deploy, testes
CLAUDE.md   # instruções para o Claude Code
```

## Documentação

Comece por [`CLAUDE.md`](CLAUDE.md) e siga o índice dali. Para construir o projeto inteiro com o Claude Code, use o prompt de [`docs/00-KICKOFF-PROMPT.md`](docs/00-KICKOFF-PROMPT.md).

## Aviso

Os episódios usam **vozes sintéticas** e comentam obras de terceiros (a fonte primária e, se usado, o material de confronto). Cite sempre as fontes (o app gera `fontes.md`). Veja [`docs/08-LEGAL-E-ETICA.md`](docs/08-LEGAL-E-ETICA.md).
