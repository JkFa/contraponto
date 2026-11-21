# Prompt de partida para o Claude Code

Abra o Claude Code na pasta vazia do projeto (com estes `.md` copiados para dentro) e cole o texto abaixo.

---

```text
Leia CLAUDE.md e todos os arquivos em docs/. Construa o projeto Contraponto inteiro,
de ponta a ponta, em modo autônomo, seguindo docs/09-TAREFAS.md milestone por milestone.

O núcleo do produto é o PROMPT MESTRE de confrontação/exame/verificação em
docs/04-PIPELINE-E-PROMPTS.md §3 — ele é sempre aplicado ao roteiro, nos dois modos
(crítica e react), com ou sem material de confronto. Não simplifique isso para um
resumo comum; o schema do roteiro (docs/03-API.md) inclui "verification" e "verdict"
e eles são obrigatórios.

Regras:
- Antes de escrever qualquer UI, invoque a skill frontend-design e siga docs/05-DESIGN-UI.md.
- Não peça confirmação para decisões de rotina. Pare só para: segredos que faltam,
  ações irreversíveis ou risco legal (ver CLAUDE.md §2).
- Comece pelo modo MOCK (MOCK_LLM=1, MOCK_TTS=1) para provar o fluxo completo sem chaves,
  incluindo um episódio com fonte primária + material de confronto e um sem confronto.
- Ao fim de cada milestone: rodar make test e make lint, fazer commit, marcar [x] em docs/09-TAREFAS.md.
- Crie o repositório público JkFa/contraponto com `gh repo create`, faça push,
  configure o GitHub Pages por GitHub Actions e prepare o Space do Hugging Face
  (Dockerfile + README com front-matter). Documente os passos que dependem de mim em docs/06-DEPLOY.md.
- Abra o app no navegador (Brave/Chrome) e confira as telas em 390 px e 1280 px antes de dar a UI como pronta,
  incluindo a tela de Revisão com o painel de verificação.
- No final, rode o checklist de docs/07-TESTES-E-QUALIDADE.md §5 e me entregue:
  URL do frontend, URL do backend e a lista curta do que só eu posso fazer (ex.: colar a GEMINI_API_KEY no Space).

Comece agora.
```

---

## Depois que o Claude Code terminar

Só você consegue fazer:
1. Criar a chave gratuita em `aistudio.google.com` e colar como **secret** `GEMINI_API_KEY` no Space.
2. (Opcional) criar chave no `console.groq.com` para o fallback (`GROQ_API_KEY`).
3. Colar a URL do Space na variável `VITE_API_URL` do repositório no GitHub (Settings → Secrets and variables → Actions → Variables).
