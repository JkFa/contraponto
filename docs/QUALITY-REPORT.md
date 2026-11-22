# Relatório de qualidade

Critérios em `docs/07-TESTES-E-QUALIDADE.md §3`.

## Episódios de qualidade (22/11/2026, backend no Render, Gemini real, vozes Edge, 3 min)

Materiais escritos para o teste (fictícios, sem obra de terceiros) para não depender do YouTube a partir do IP do
servidor. Todos passaram pelo validador; verificação conferida item a item manualmente.

| # | Caso | Material | Resultado | Problemas | Correções |
|---|---|---|---|---|---|
| 1 | crítica **com** confronto | coluna sobre home office × notas com dados de 1.200 empresas | 4 itens corretos (2 contestadas, 1 parcial, 1 não verificável/interna); 2 citações literais da primária; veredito "Com base no que temos aqui…"; 70 s roteiro + 60 s áudio; −16,4 LUFS | roteiro curto (357 palavras, alvo 360–540); modelo `gemini-2.5-flash` dava 404 | prompt passou a exigir mínimo de palavras e nº de falas; modelo padrão `gemini-3.6-flash` + descoberta automática em 404 |
| 2 | react **com** confronto | divulgação de app "Foco+" × resumo sobre sons binaurais e grupo de controle | 4 itens corretos (3 contestadas, 1 parcial), todos `evidence_role=confronto`; 449 palavras; 1 citação; 126 s + 65 s; −16,5 LUFS | nenhum | — |
| 3 | crítica **sem** confronto | discurso sobre ciclovia (impressões, 40% sem fonte) | 4 itens `nao_verificavel/interna` com o critério certo (impressão pessoal, número sem fonte, causalidade sem dado, generalização); 3 citações (máximo); 504 palavras; 53 s + 71 s; −16,3 LUFS | nenhum | — |
| 4 | react, texto colado, **sem** confronto | post "2 litros de água obrigatórios" | 1ª tentativa: `SCRIPT_INVALID` (3 respostas fora do formato). Após correção: 5 itens (4 não verificáveis, 1 contestada por salto lógico — a anedota da avó); 465 palavras; 97 s + 61 s; −16,4 LUFS | rótulos de confronto usados sem confronto; 2 citações com moldura ("o autor decreta: '…'") — ambas sinalizadas pelo verificador de fidelidade | normalização automática de rótulos sem confronto; log com o motivo do validador; regra no prompt: citação contém só o trecho literal |

| Critério (`docs/07 §3`) | Resultado |
|---|---|
| Afirmações sobre as fontes sem respaldo | 0 encontradas (nenhum episódio trouxe dado externo ao material) |
| Citações ≤ 3 por fonte, ≤ 15 palavras, `role` correto | ok nos 4; 2 citações com moldura no ep. 4 foram sinalizadas ao revisor |
| `verification` reflete o confronto / exame interno | ok, conferido item a item |
| `verdict` honesto e proporcional, linguagem de episódio | ok ("Com base no que temos aqui / no material examinado…") |
| Opinião separada de fato | ok (`opiniao` × `contexto`/`confronto`) |
| Vozes: loudness | −16,3 a −16,5 LUFS (meta −16 ±2); escuta humana de cortes/pronúncia **pendente** |
| Tempo (meta < 5 min para 5 min de episódio) | 2–3 min para episódios de 3 min no plano free do Render; 5 min ainda não medido |
| `verificacao.md` e `fontes.md` | gerados e corretos |

**YouTube a partir do servidor (22/11/2026):** um link real do YouTube enviado ao backend no Render resultou em
`TRANSCRIPT_UNAVAILABLE` — o YouTube bloqueia a leitura de transcrições a partir do IP do Render (risco já previsto no
PRD). O fallback funciona: a tela "Esse vídeo não deixou a gente ler a transcrição" aparece no site e o usuário cola o
texto. A aba "Link do YouTube" agora avisa isso de antemão. A partir de uma máquina residencial (`make dev`), a
ingestão do YouTube funciona (testado localmente).

## Episódio de 5 min (22/11/2026)

React com confronto (redes sociais e saúde mental, materiais fictícios): roteiro em 64 s + áudio em 105 s =
**169 s no total** para um episódio de **4 min 17 s** (meta < 5 min ✔). 625 palavras (mín. 600), 5 afirmações
verificadas contra o confronto (3 contestadas, 2 parciais), 4 citações (2 por fonte, `role` corretos), nenhum aviso de
fidelidade, veredito proporcional ("levanta uma preocupação legítima… mas…"), −16,5 LUFS.

## Escuta automatizada (proxy da escuta humana)

Os MP3 dos episódios 2–4 foram transcritos com Whisper (`small`, pt) e comparados palavra a palavra com o texto
enviado às vozes (`tts_prepare`):

| Episódio | Palavras esperadas | Ouvidas | Erro por palavra | Trechos faltando/sobrando (≥ 3 palavras) |
|---|---|---|---|---|
| 2 | 449 | 442 | ≈ 6,0 % | nenhum |
| 3 | 507 | 502 | ≈ 3,9 % | nenhum |
| 4 | 466 | 463 | ≈ 3,0 % | nenhum |

- **Sem cortes:** nenhuma fala ou trecho sumiu.
- **Números:** quase todas as "diferenças" são o Whisper escrevendo por algarismos o que a voz leu por extenso
  ("quarenta por cento" → "40", "noventa e oito" → "98"), ou seja, os números foram lidos em voz alta corretamente.
- Diferenças restantes (ex.: "como justificativa" → "para a certificativa", "Foco mais" → "focomais") parecem erro do
  reconhecedor, não da voz — **confirmar na escuta humana**.

## Download no navegador

Teste E2E (Playwright, Chromium — mesmo motor do Brave e do Chrome) clica em **Baixar MP3** e em **Verificação (.md)**
e confirma um download real (`.mp3` com conteúdo; `verificacao.md` com o veredito).

Pendências que dependem de pessoa/aparelho: escuta humana dos MP3 (pronúncia, naturalidade), download no **Brave**
propriamente dito e **Web Share no Android** (a API não existe no Chrome de desktop Linux; a ordem de fallback
arquivo → link → menu está coberta por testes unitários).

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
