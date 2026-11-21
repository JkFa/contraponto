# 06 — Deploy (GitHub Pages + Hugging Face Space)

## 1. Por que essa combinação

| Camada | Plataforma | Por quê |
|---|---|---|
| Frontend | **GitHub Pages** | Estático, grátis, sem domínio próprio, sem restrição de uso comercial, tudo no GitHub do usuário (`JkFa`) |
| Backend | **Hugging Face Space (Docker, CPU basic)** | Grátis, aceita Python + FFmpeg, HTTPS pronto |
| Alternativa de frontend | **Vercel** | Só se o usuário pedir. O plano Hobby é restrito a uso não comercial |

URLs esperadas:
- Frontend: `https://jkfa.github.io/contraponto/`
- Backend: `https://<usuario-hf>-contraponto.hf.space`

## 2. Repositório (automatizar com `gh`)

```bash
gh auth status                                   # deve estar logado; se não, pedir ao usuário `gh auth login`
git init -b main && git add -A && git commit -m "chore: initial scaffold"
gh repo create JkFa/contraponto --public --source=. --remote=origin --push
```

## 3. Frontend → GitHub Pages

### 3.1 Configuração
- `apps/web/vite.config.ts`: `base: '/contraponto/'`.
- Roteamento com **`HashRouter`** (Pages não faz fallback de SPA).
- `VITE_API_URL` lido por `import.meta.env.VITE_API_URL`.
- Incluir `apps/web/public/404.html` (cópia do `index.html`) por segurança e `.nojekyll`.

### 3.2 Workflow `.github/workflows/deploy-web.yml`

```yaml
name: Deploy web
on:
  push:
    branches: [main]
    paths: ["apps/web/**", ".github/workflows/deploy-web.yml"]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  build:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: apps/web } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm, cache-dependency-path: apps/web/package-lock.json }
      - run: npm ci
      - run: npm run lint && npm test -- --run
      - run: npm run build
        env:
          VITE_API_URL: ${{ vars.VITE_API_URL }}
      - uses: actions/upload-pages-artifact@v3
        with: { path: apps/web/dist }
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

### 3.3 Ativar o Pages por CLI

```bash
gh api -X POST repos/JkFa/contraponto/pages -f build_type=workflow || \
gh api -X PUT  repos/JkFa/contraponto/pages -f build_type=workflow
gh variable set VITE_API_URL --body "https://<usuario-hf>-contraponto.hf.space" --repo JkFa/contraponto
gh workflow run deploy-web.yml --repo JkFa/contraponto
```

## 4. Backend → Hugging Face Space (Docker)

### 4.1 `apps/api/Dockerfile`

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user . .
ENV PORT=7860 DATA_DIR=/tmp/contraponto
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
```

### 4.2 `apps/api/README.md` (front-matter obrigatório do Space)

```markdown
---
title: Contraponto API
emoji: 🎙️
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---
Backend do Contraponto (FastAPI + FFmpeg).
```

### 4.3 Publicação
O conteúdo de `apps/api/` vai para a **raiz** do repositório do Space.

```bash
pip install -U huggingface_hub           # fornece o CLI `hf`
hf auth login                             # PASSO DO USUÁRIO: token com permissão de escrita
hf repo create contraponto --type space --space-sdk docker
git clone https://huggingface.co/spaces/<usuario-hf>/contraponto /tmp/space
rsync -a --delete --exclude '__pycache__' --exclude '.venv' apps/api/ /tmp/space/
cd /tmp/space && git add -A && git commit -m "deploy" && git push
```

Criar o script `scripts/deploy_space.sh` com esses passos (idempotente), para o usuário rodar `make deploy-api`.

### 4.4 Secrets do Space (PASSO DO USUÁRIO)
Space → Settings → **Variables and secrets**:

| Nome | Tipo | Valor |
|---|---|---|
| `GEMINI_API_KEY` | Secret | chave do `aistudio.google.com` |
| `GROQ_API_KEY` | Secret | (opcional) `console.groq.com` |
| `ALLOWED_ORIGINS` | Variable | `https://jkfa.github.io,http://localhost:5173` |
| `PUBLIC_BASE_URL` | Variable | URL do Space (usada em `share_url`) |

> **Estado em 21/11/2026:** não havia `GEMINI_API_KEY` nem `GROQ_API_KEY` no ambiente de desenvolvimento.
> Todo o desenvolvimento e os testes rodaram em modo mock (`MOCK_LLM=1`). O primeiro roteiro real acontece
> quando a chave for colada no Space (ou em `.env` local) — ver `docs/QUALITY-REPORT.md`.
> Sem chave configurada, o backend responde `LLM_NOT_CONFIGURED` e a UI orienta a usar a própria chave (BYOK em Ajustes).

### 4.5 Comportamento do Space gratuito
- Dorme após inatividade; a primeira chamada acorda em ~30–60 s (UI deve avisar).
- Disco é **efêmero**: reinício apaga episódios → por isso o TTL de 24 h e o aviso "baixe para guardar".
- Se o YouTube bloquear o IP do Space: usar fallback de colar texto ou rodar localmente.

### 4.6 TTS: fallback
O provedor padrão é `edge-tts`. O fallback Piper (opcional em `docs/04 §5`) **não foi implementado**: se o Edge falhar
após os retries, o episódio vai para `TTS_FAILED` e o usuário pode tentar de novo. Fica no backlog.

## 5. `.env.example`

```dotenv
# LLM
GEMINI_API_KEY=
GEMINI_MODEL=            # ajustar para o modelo Flash gratuito vigente
GROQ_API_KEY=
GROQ_MODEL=
LLM_PROVIDER=gemini      # gemini | groq | mock
# TTS
TTS_PROVIDER=edge        # edge | piper | mock
VOICE_HOST_1=pt-BR-AntonioNeural
VOICE_HOST_2=pt-BR-FranciscaNeural
# Mocks (dev sem chaves)
MOCK_LLM=0
MOCK_TTS=0
# Servidor
ALLOWED_ORIGINS=http://localhost:5173
PUBLIC_BASE_URL=http://localhost:8000
DATA_DIR=./.data
EPISODE_TTL_HOURS=24
MAX_CONCURRENT_RENDERS=2
# Frontend (apps/web/.env.local)
VITE_API_URL=http://localhost:8000
```

## 6. CI (`.github/workflows/ci.yml`)
- Job **web:** `npm ci`, `npm run lint`, `npm test -- --run`, `npm run build`.
- Job **api:** `python 3.11`, instalar `ffmpeg`, `pip install -r requirements.txt`, `ruff check`, `pytest` (com `MOCK_LLM=1 MOCK_TTS=1`).
- Executa em `push` e `pull_request`.

## 7. Alternativa: frontend na Vercel (só se pedido)

```bash
npm i -g vercel && cd apps/web && vercel --prod
```
- Framework: Vite; `base: '/'`; definir `VITE_API_URL` no painel; adicionar o domínio `*.vercel.app` em `ALLOWED_ORIGINS`.
- Observação: o plano Hobby é para uso pessoal/não comercial. Se o produto virar comercial, manter GitHub Pages ou migrar para plano pago.

## 8. Checklist de publicação

- [ ] Repo `JkFa/contraponto` criado e com push
- [ ] Workflow de deploy do web verde e site abrindo em `https://jkfa.github.io/contraponto/`
- [ ] Space criado, build verde, `GET /api/health` responde
- [ ] Secrets configurados (passo do usuário)
- [ ] `VITE_API_URL` apontando para o Space; web redeployado
- [ ] CORS testado a partir do site publicado
- [ ] Fluxo completo com um vídeo real, no site publicado
