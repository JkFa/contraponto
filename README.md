# Contraponto

Gere um episódio de podcast com **duas vozes** que **examina, confronta e verifica** as informações de um vídeo, texto ou arquivo — comparando-as, se você quiser, com um material próprio que você fornece. Revise o roteiro, baixe o MP3 e compartilhe.

> Nome de trabalho. Custo zero: GitHub Pages + Hugging Face Space + free tiers.

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
