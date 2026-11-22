# Contraponto

Gere um episódio de podcast com **duas vozes** que **examina, confronta e verifica** as informações de um vídeo, texto ou arquivo — comparando-as, se você quiser, com um material próprio que você fornece. Revise o roteiro, baixe o MP3 e compartilhe.

> Nome de trabalho. Custo zero: GitHub Pages + Render (plano free) + free tiers.

## Endereços

| | URL | Estado |
|---|---|---|
| Frontend | https://jkfa.github.io/contraponto/ | publicado (GitHub Pages) |
| Backend | https://contraponto-api-fgcv.onrender.com | publicado (Render, plano free; dorme após 15 min sem uso) |
| Repositório | https://github.com/JkFa/contraponto | público |

Localmente tudo funciona com `make mock` (sem chaves) ou `make dev` (com chave em `.env`).

### Como foi colocado no ar (para refazer do zero)

1. Em https://render.com (login com GitHub): **New → Blueprint** → repositório `JkFa/contraponto`.
2. Quando pedir, colar o secret `GEMINI_API_KEY` (crie em `aistudio.google.com`); `GROQ_API_KEY` é opcional.
3. Com o deploy verde, ligar o site ao backend:
   `gh variable set VITE_API_URL --body "https://<url-do-serviço>.onrender.com" --repo JkFa/contraponto`
   e `gh workflow run deploy-web.yml --repo JkFa/contraponto`.

Detalhes e limites do plano free em [`docs/06-DEPLOY.md §4R`](docs/06-DEPLOY.md). O Hugging Face Space continua
possível (`make deploy-api`), mas desde 22/11/2026 exige assinatura PRO para Docker.

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
apps/api    # FastAPI (Render, Docker)
docs/       # PRD, arquitetura, API, prompts, design, deploy, testes
CLAUDE.md   # instruções para o Claude Code
```

## Documentação

Comece por [`CLAUDE.md`](CLAUDE.md) e siga o índice dali. Para construir o projeto inteiro com o Claude Code, use o prompt de [`docs/00-KICKOFF-PROMPT.md`](docs/00-KICKOFF-PROMPT.md).

## Aviso

Os episódios usam **vozes sintéticas** e comentam obras de terceiros (a fonte primária e, se usado, o material de confronto). Cite sempre as fontes (o app gera `fontes.md`). Veja [`docs/08-LEGAL-E-ETICA.md`](docs/08-LEGAL-E-ETICA.md).
