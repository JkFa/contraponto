# 01 — PRD (Product Requirements)

## 1. Problema

Quem quer comentar um vídeo, artigo ou documento normalmente só consegue **resumi-lo**. Contraponto faz algo diferente: **examina** o material — confrontando-o com um segundo material que o próprio usuário traz, ou com critérios de consistência interna — e entrega isso em áudio, com o usuário no controle da tese e da revisão.

## 2. Público

- Professores, criadores de conteúdo, estudantes e jornalistas que querem checar ou confrontar um material em áudio.
- Uso pessoal e demonstração (o usuário é o dono do produto; pode virar produto no futuro).

## 3. As duas entradas

O produto trabalha com **até duas fontes**, nunca uma só sendo tratada como verdade absoluta:

| Papel | Obrigatória? | O que é | Formatos |
|---|---|---|---|
| **Fonte primária** | Sim | O material que será examinado | Link do YouTube, texto colado, arquivo (`.txt`, `.srt`, `.pdf`) |
| **Material de confronto** | Não | O material que o usuário traz para **checar, contestar ou confirmar** a fonte primária — um artigo divergente, dados oficiais, uma transcrição de outra fala, notas próprias, uma errata | Link do YouTube, texto colado, arquivo (`.txt`, `.srt`, `.pdf`) |

Limites: cada fonte até ~2 h de vídeo / 60 000 caracteres de texto / 5 MB de arquivo (ver `docs/03-API.md`).

Quando **não há** material de confronto, o exame não desaparece: a IA aplica um **exame de consistência interna** (lacunas lógicas, generalizações sem dado, ausência de fonte citada, contradições dentro do próprio material) — ver `docs/04-PIPELINE-E-PROMPTS.md §3.4`.

## 4. O núcleo: prompt mestre de confrontação/exame/verificação

**Isto é o que diferencia o produto de um "resumidor de vídeo".** Toda geração de roteiro passa por um prompt mestre, sempre ativo, que obriga a IA a:

1. **Extrair** as afirmações centrais da fonte primária.
2. **Confrontá-las** com o material de confronto (quando houver) — ou examinar a consistência interna (quando não houver).
3. **Examinar** a força de cada afirmação: tem dado, é generalização, é opinião disfarçada de fato, falta contexto.
4. **Verificar** o resultado: cada afirmação central recebe um status — `apoiada`, `contestada`, `parcial` ou `não verificável` — registrado em `script.verification` (schema em `docs/03-API.md`).
5. **Fechar com um veredito curto** (`script.verdict`): o que se sustenta, o que não se sustenta, o que fica em aberto.

Isso vale **nos dois modos** (`crítica` e `react`). O que muda entre os modos é só quem traz a tese condutora — não se o exame acontece.

## 5. Modos

| Modo | Entrada extra | Quem conduz a tese | O confronto entra como |
|---|---|---|---|
| **Crítica** | Tese do usuário (obrigatória, 1–2 000 caracteres) | O usuário | Evidência a favor ou contra a tese |
| **React** | Nenhuma (opcional: "pontos de atenção") | A IA, a partir do próprio exame | Insumo central do exame, não de uma tese pré-definida |

Parâmetros comuns: **duração alvo** (3, 5, 8 ou 12 min), **tom** (`descontraído` | `analítico` | `provocativo-respeitoso`), **nomes dos apresentadores** (padrão: "Davi" e "Lia").

## 5. Fluxo do usuário (happy path)

1. Cola a fonte primária → (opcional) adiciona material de confronto → escolhe modo → (escreve a tese, se `crítica`) → **Gerar roteiro**.
2. Vê o progresso: *Lendo as fontes → Cruzando as informações → Escrevendo o roteiro*.
3. **Tela de revisão**: lê/edita as falas, vê as citações com timestamp, e o **painel de verificação** (cada afirmação central com seu status: apoiada/contestada/parcial/não verificável) e o veredito final. Botões: *Regenerar*, *Aprovar e gerar áudio*.
4. Vê o progresso: *Gravando vozes → Mixando*.
5. **Tela do episódio**: player com waveform, **Baixar MP3**, **Compartilhar**, **Copiar link**, **Baixar roteiro (.md)**, **Baixar verificação (.md)**, **Baixar fontes (.md)**.

## 6. Requisitos funcionais

- **RF1** Extrair transcrição do YouTube sem baixar mídia; fallback de colar texto/arquivo. Vale para a fonte primária e, se usada, a de confronto.
- **RF2** Gerar roteiro JSON validado por schema (ver `docs/04`), com no máximo **3 citações literais por fonte** (primária e confronto, contadas separadamente), cada uma de até 15 palavras e com timestamp quando a fonte tiver.
- **RF3** Aplicar o **prompt mestre de confrontação/exame/verificação** (seção 4) em toda geração, preenchendo `script.verification` e `script.verdict`.
- **RF4** Quando não houver material de confronto, aplicar exame de consistência interna em vez de pular a verificação.
- **RF5** Revisão humana obrigatória antes do áudio (não existe "gerar tudo direto" no MVP).
- **RF6** Editar falas e itens de verificação do roteiro (texto) e regenerar o roteiro inteiro.
- **RF7** Sintetizar áudio com duas vozes pt-BR distintas, pausas naturais e (opcional) trilha de fundo CC0.
- **RF8** Progresso em tempo real (SSE) com mensagens em pt-BR, incluindo a etapa de cruzamento das fontes.
- **RF9** Download do MP3, `roteiro.md`, `roteiro.json`, `verificacao.md` e `fontes.md`.
- **RF10** Compartilhar: Web Share API (com o arquivo quando suportado), copiar link, página pública do episódio `/s/{id}` com player e metadados Open Graph.
- **RF11** Histórico local: lista de episódios recentes no `localStorage` (id, título, data), para reabrir enquanto o backend ainda os tiver.
- **RF12** BYOK opcional: usuário informa a própria chave Gemini (guardada só no navegador, enviada em header, nunca registrada em log).

## 7. Requisitos não funcionais

- **Custo:** zero recorrente.
- **Desempenho:** episódio de 5 min gerado (roteiro + áudio) em menos de 5 min em CPU comum, mesmo com as duas fontes.
- **Privacidade:** não registrar conteúdo dos usuários em log; apagar episódios após 24 h.
- **Robustez:** retries com espera, fallback de LLM e de TTS, mensagens de erro acionáveis.
- **Acessibilidade:** WCAG AA; o episódio sempre acompanha transcrição legível.
- **Responsivo:** mobile-first (390 px) até desktop (1280 px+).

## 8. Fora do escopo (MVP)

- Avatar, vídeo, audiograma (fase 2).
- Login, contas, banco de dados, pagamentos.
- Publicação automática no YouTube/Spotify.
- Clonagem de voz de pessoas reais.
- Bot do Telegram (fase 2).
- Mais de uma fonte de confronto por episódio (fica em uma só, no MVP).

## 9. Métricas de sucesso

- 3 de 3 episódios de teste sem afirmação sem respaldo na checagem manual.
- Em pelo menos 1 dos 3 episódios de teste, usar material de confronto e conferir que `script.verification` reflete corretamente apoio/contestação.
- Tempo até o primeiro áudio < 5 min para 5 min de episódio.
- Download e compartilhamento funcionando em Brave desktop e Chrome Android.

## 10. Riscos

| Risco | Mitigação |
|---|---|
| YouTube bloqueia IP do Space | Fallback "cole a transcrição"; modo local (`make dev`) |
| Edge-TTS muda ou cai | Piper local como fallback |
| Free tier do LLM esgota | Fallback Groq; blocos menores; BYOK |
| Abuso do backend público | Rate limit por IP, limites de tamanho/duração, TTL |
| Reclamação de autor de qualquer uma das fontes | `docs/08`: citação mínima por fonte, crédito, transparência |
| IA tratar o confronto como automaticamente "certo" | Prompt mestre exige expor a contradição, não arbitrar; ver `docs/04 §3.3` |
| IA inventar status de verificação sem base | Validador rejeita item de `verification` sem `note` que aponte de onde vem o julgamento |
