# 07 — Testes e qualidade

## 1. Estratégia

| Camada | Ferramenta | O que cobrir |
|---|---|---|
| API unitário | `pytest` | extração de `video_id` (×2 fontes), SSRF, normalização, prompt mestre (montagem), validador de roteiro, validador de `verification`/`verdict`, verificador de citações por fonte, TTL, rate limit |
| API integração | `pytest` + `httpx.AsyncClient` | fluxo completo com `MOCK_LLM=1 MOCK_TTS=1`: criar (com e sem confronto) → SSE → revisar → renderizar → baixar MP3/verificação |
| Web unitário | `vitest` + Testing Library | Composer, ConfrontoInput (validação, estado fechado/aberto), ShareMenu (ordem de fallback), VerificationPanel (mapeamento status → selo), `lib/share.ts`, `lib/format.ts` |
| Web E2E | `playwright` (Chromium) | fluxo feliz no modo mock, com e sem confronto; captura de tela 390 px e 1280 px |
| Acessibilidade | `@axe-core/playwright` | zero violações "serious/critical" nas 4 telas, incluindo o painel de verificação |

## 2. Casos obrigatórios

**Entrada e segurança**
- URL de `youtube.com`, `youtu.be`, `/shorts/` válidas → ok; `evil.com/watch?v=…`, `file://`, `http://169.254.169.254` → `INVALID_URL`. Mesma regra para `confronto_youtube_url`.
- Texto > 60 000 caracteres (primário ou confronto) → `413 INPUT_TOO_LONG`. Arquivo > 5 MB → `413`. `.exe` → `422 FILE_UNSUPPORTED`.
- Mais de um campo de confronto preenchido ao mesmo tempo → `422 MULTIPLE_CONFRONTO_INPUTS`.
- PDF escaneado (sem texto) → `PDF_NO_TEXT`, em qualquer uma das duas fontes.
- Header `X-Gemini-Key` nunca aparece em log (teste que captura logs).
- CORS: origem não permitida é bloqueada.

**Prompt mestre e verificação**
- Com material de confronto: roteiro gerado tem `verification` com `evidence_role` apontando `"confronto"` em pelo menos um item, e há pelo menos um turno `kind="confronto"` correspondente.
- Sem material de confronto: todos os itens de `verification` têm `evidence_role: "interna"`; nenhum turno usa `kind="confronto"`.
- `verification` com menos de 3 ou mais de 8 itens é rejeitado/reparado.
- Item de `verification` com `note` vazia é rejeitado.
- `verdict` ausente ou vazio é rejeitado.
- Roteiro com 4 citações da mesma fonte é rejeitado/reparado; citação > 15 palavras é rejeitada; citação da fonte de confronto marcada com `role="primaria"` (ou vice-versa) é rejeitada.
- Citação inexistente na fonte indicada por `role` gera `fidelity_notes`.
- Modo `critica` sem `thesis` → `422`.
- Falantes alternando; nenhum turno > 600 caracteres.

**Fluxo**
- Não é possível `render` fora de `script_ready` (`409`).
- Editar roteiro (incluindo itens de `verification`) e renderizar usa a versão editada.
- Episódio expirado → `404 EXPIRED`; limpeza apaga arquivos.
- Duas renderizações simultâneas respeitam `MAX_CONCURRENT_RENDERS`.

**Áudio**
- MP3 final existe, `duration_s > 0`, `Range` funciona, `?download=1` define `Content-Disposition`.
- Loudness dentro de −16 ±2 LUFS (checar com `ffmpeg ebur128`).

**Frontend**
- `ConfrontoInput`: fechado por padrão; abrir e preencher adiciona o campo correto ao `FormData`; remover limpa; só aceita um tipo de entrada por vez.
- `VerificationPanel`: cada status renderiza selo + rótulo de texto (nunca só cor); clicar num item rola até a fala relacionada.
- `ShareMenu`: com `canShare({files})` usa arquivo; sem isso, usa `share` de URL; sem `navigator.share`, mostra fallback desktop; `AbortError` não gera toast de erro.
- Falha de transcrição (de qualquer uma das fontes) mostra o painel "Cole o texto" certo e reenvia mantendo modo/tese/confronto.
- Backend dormindo mostra "Acordando o estúdio…".

## 3. Teste de qualidade com material real (manual, obrigatório)

Gerar **4 episódios** e conferir:

1. `crítica` **com** material de confronto.
2. `react` **com** material de confronto.
3. `crítica` **sem** confronto (exame interno).
4. `react` a partir de texto colado, **sem** confronto.

| Critério | Meta |
|---|---|
| Afirmações sobre as fontes sem respaldo | **0** |
| Citações literais | ≤ 3 por fonte, cada ≤ 15 palavras, com timestamp e `role` corretos |
| `verification` reflete corretamente o confronto (ou o exame interno) | sim, checado manualmente item a item |
| `verdict` é honesto e proporcional (nem elogio nem demolição automáticos) | sim |
| Opinião separada de fato de cada fonte | sim (`kind`, `role` e linguagem) |
| Vozes: sem cortes, símbolos lidos em voz alta, números estranhos | nenhum |
| Tempo (5 min de episódio) | < 5 min no total |
| `verification.md` e `fontes.md` | gerados e corretos |

Registrar o resultado em `docs/QUALITY-REPORT.md` (tabela simples com data, material, resultado, problemas e correções).

## 4. Lint e tipos

- `ruff check` + `ruff format --check`; `tsc --noEmit`; `eslint` sem warnings.
- Cobertura mínima sugerida: 80% nos módulos `ingest`, `script_service`, `verification`, `mix`.

## 5. Checklist final de aceite (definição de pronto)

Marque somente após **executar** cada item.

- [x] `make test` e `make lint` verdes
- [x] `make mock` roda o fluxo completo sem chaves, com e sem confronto
- [x] Frontend publicado e abrindo no GitHub Pages
- [ ] Backend no Space com `GET /api/health` ok
- [ ] Fluxo real: fonte primária + material de confronto → roteiro com verificação → revisão → áudio → MP3 baixado
- [ ] Fluxo real: só fonte primária (sem confronto) → exame interno → roteiro → áudio
- [x] Fallback "cole o texto" funcionando quando a transcrição de qualquer fonte falha
- [ ] **Download** do MP3 e da verificação funciona no Brave desktop
- [ ] **Compartilhar**: Web Share no Android (ou fallback), copiar link, página `/s/{id}` abre com player e veredito
- [x] Axe sem violações sérias; navegação por teclado completa; selos de status com rótulo de texto
- [x] Telas conferidas em 390 px e 1280 px (capturas em `docs/screens/`)
- [ ] 4 episódios de qualidade avaliados (`docs/QUALITY-REPORT.md`)
- [x] Nenhum segredo no repositório (`git log -p | grep -i "api_key"` limpo)
- [ ] `docs/08-LEGAL-E-ETICA.md` cumprido (selo, fontes, limites de citação por fonte)
- [ ] `README.md` com URLs finais
