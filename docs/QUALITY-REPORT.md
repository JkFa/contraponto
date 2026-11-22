# Relatório de qualidade

Critérios em `docs/07-TESTES-E-QUALIDADE.md §3`.

## Situação

Os **4 episódios de qualidade com material real ainda não foram avaliados**: exigem um LLM real, e não havia
`GEMINI_API_KEY`/`GROQ_API_KEY` disponível durante o desenvolvimento. Assim que a chave estiver no Space (ou em `.env`),
gerar os quatro casos abaixo e preencher a tabela.

| Data | Caso | Material | Resultado | Problemas | Correções |
|---|---|---|---|---|---|
| — | 1. crítica com confronto | — | pendente | — | — |
| — | 2. react com confronto | — | pendente | — | — |
| — | 3. crítica sem confronto | — | pendente | — | — |
| — | 4. react, texto colado, sem confronto | — | pendente | — | — |

## O que já foi verificado com material real (LLM simulado)

| Data | Teste | Resultado |
|---|---|---|
| 22/11/2026 | Ingestão real do YouTube (`youtube-transcript-api` 1.2.5) com timestamps e oEmbed | ok |
| 22/11/2026 | Vozes reais `edge-tts` (Antonio + Francisca), roteiro mock de 3 min com e sem confronto | ok: MP3 de 2 min 18 s em 22 s de render |
| 22/11/2026 | Loudness do MP3 real (`ebur128`) | −16,4 LUFS (meta −16 ±2) |
| 22/11/2026 | Tags ID3 (título, "Contraponto (vozes sintéticas)", URL da fonte) | ok |
| 22/11/2026 | `fontes.md`/`verificacao.md` com fonte real, data de acesso e citações com timestamp | ok |
| 22/11/2026 | Logs sem conteúdo do usuário nem chave BYOK | ok (teste automatizado + inspeção do log) |
| 22/11/2026 | Imagem Docker do Space (`/api/health`) | ok |
