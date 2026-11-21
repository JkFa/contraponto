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

Recebe uma fonte primária (e, opcionalmente, um material de confronto), gera um roteiro de podcast
que examina e verifica as afirmações da fonte, e sintetiza o episódio com duas vozes sintéticas.

Contrato da API: `docs/03-API.md` no repositório principal.
