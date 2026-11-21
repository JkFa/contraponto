# 05 — Design e UI/UX

> **Obrigatório:** invocar a skill `frontend-design` antes de escrever UI e usar este documento como briefing. A skill refina a execução; a direção abaixo é o ponto de partida.

## 1. Conceito: "estúdio de rádio à noite"

O app é um **estúdio de gravação que também é uma redação de checagem**. O usuário entra, traz uma fonte (e, se quiser, algo para confrontá-la), pendura a luz **NO AR** (vermelha) quando gera, e sai com um episódio e uma tabela de verificação. Sensação: **editorial, quente, tátil, concentrada** — nada de "dashboard SaaS genérico".

Palavras-guia: *microfone, fita, mesa de som, jornal impresso, luz de estúdio, mesa de checagem*.

## 2. Tokens (`styles/tokens.css`)

Tema escuro por padrão, com tema claro "papel" opcional (`prefers-color-scheme` + alternador).

```css
:root {
  /* superfícies */
  --ink-950: #0d0c0b;   /* fundo */
  --ink-900: #151311;   /* painéis */
  --ink-800: #1e1b18;   /* elevação */
  --line:    #2d2924;   /* divisórias */
  /* texto */
  --paper:   #f4ecdf;   /* texto principal */
  --paper-dim: #b9ae9b; /* texto secundário (contraste ≥ 4.5:1 sobre ink-900) */
  /* sinais */
  --onair:   #e8412a;   /* acento principal: NO AR, CTA */
  --amber:   #f2a93b;   /* acento secundário: citações, avisos */
  --sage:    #8fb996;   /* status: apoiada */
  --rust:    #c96a4a;   /* status: contestada */
  --sand:    #c9b36a;   /* status: parcial / não verificável */
  --host-1:  #7fb2c9;   /* cor do apresentador 1 */
  --host-2:  #e0a08a;   /* cor do apresentador 2 */
  /* forma */
  --radius-s: 4px; --radius-m: 10px;
  --shadow-lamp: 0 0 24px color-mix(in oklab, var(--onair) 55%, transparent);
}
```

Verificar contraste de **todos** os pares texto/fundo (AA). Texto de botão sobre `--onair` deve ser `--ink-950` ou branco conforme o melhor contraste.

## 3. Tipografia

- **Display:** serifa de personalidade (ex.: *Fraunces*, *Instrument Serif* ou *Newsreader*) em títulos e no título do episódio. Pesos altos, `optical size` ligado.
- **Corpo:** grotesca humanista, **não** Inter/Roboto/Arial (ex.: *Bricolage Grotesque*, *Hanken Grotesk*, *Instrument Sans*).
- **Mono:** *IBM Plex Mono* ou *JetBrains Mono* para timestamps, rótulos de estado, status de verificação e "contador de fita".
- Fontes via `@fontsource` (autohospedadas, sem requisição a terceiros). `font-display: swap`.
- Escala: base 17–18 px no mobile; títulos com `clamp()`.

## 4. Composição e movimento

- **Layout:** grid assimétrico no desktop (coluna de entrada larga + trilho lateral com "Últimos episódios"); coluna única no mobile. Muito espaço negativo; rótulos pequenos em caixa-alta mono.
- **Textura:** grão sutil (SVG noise com baixa opacidade) no fundo; linhas finas estilo *rule* de jornal entre seções. Sem gradientes roxos, sem glassmorphism.
- **Movimento** (CSS puro; Framer Motion só se necessário):
  - Luz **NO AR** pulsa suavemente durante `scripting` e `rendering` (2.4 s).
  - Waveform animada no player, sincronizada com a reprodução.
  - Entrada das falas na revisão com *stagger* curto (30 ms por item, máx. 12).
  - Contador estilo fita (`00:00 / 04:52`) em mono.
- **`prefers-reduced-motion`:** desligar pulsos e staggers; manter apenas mudanças de estado.

## 5. Telas

### 5.1 Home (`/`)
- Título editorial: "Cole um material. Ouça o exame." + subtítulo curto.
- **Composer** (fonte primária, obrigatória): abas **Link do YouTube | Texto | Arquivo** (arrastar e soltar).
- **ConfrontoInput** (opcional, seção recolhida por padrão, abre com um botão "+ Adicionar material de confronto"): mesmas três abas, com legenda curta: "Um texto, link ou arquivo para checar o que a fonte primária afirma." Chip removível quando preenchido. Se vazio, mostrar uma linha discreta: "Sem confronto, a IA examina a consistência interna da fonte."
- **ModeSwitch:** dois cartões grandes selecionáveis — **Crítica** ("Você traz a tese") e **React** ("A IA dá a opinião"). Em *Crítica*, campo de tese com contador (0/2000) e dica: "Pode ser em tópicos soltos."
- Opções recolhíveis ("Ajustes"): duração, tom, nomes dos apresentadores, usar minha chave Gemini.
- CTA: **Gerar roteiro** (botão grande, `--onair`). Abaixo: aviso curto de privacidade/IA e de vozes sintéticas.
- Trilho "Últimos episódios" (localStorage).
- Estado "acordando o estúdio" quando o backend demora.

### 5.2 Estúdio / progresso (`/e/:id`, enquanto processa)
- Luz **NO AR** + etapa atual em frase humana ("Cruzando as informações…") + barra fina de fita com `pct`.
- Se `TRANSCRIPT_UNAVAILABLE` ou `CONFRONTO_TRANSCRIPT_UNAVAILABLE`: painel inline **"Cole o texto aqui"** (indicando de qual das duas fontes) que reenvia o pedido, mantendo o restante do formulário.

### 5.3 Revisão (`/e/:id/revisar`)
- Cabeçalho: título editável + resumo.
- Lista de falas: avatar/cor do apresentador, texto editável (textarea auto-ajustável), **chip de tipo** (contexto/citação/confronto/opinião/pergunta), chip mono com a fonte (`primária`/`confronto`) e `source_ts` nas citações (clicar abre o vídeo no tempo, em nova aba: `url&t=XXs`).
- **Painel de verificação** (seção própria, sempre visível, não escondida em aba): tabela ou cartões — uma linha por item de `verification`, com a afirmação, um **selo de status** (apoiada = `--sage`, contestada = `--rust`, parcial/não verificável = `--sand`) e a nota. O **veredito** aparece em destaque no topo ou no fim do painel, como uma citação editorial.
- **Painel de fidelidade** (lateral/colapsável, separado do de verificação): lista de `fidelity_notes` em âmbar, com atalho para a fala.
- Contador de palavras e **duração estimada** atualizados ao editar.
- Ações fixas no rodapé: **Regenerar** (com campo "instruções"), **Aprovar e gerar áudio** (principal).
- Aviso "Você é responsável pelo que publica." (uma linha, discreto).

### 5.4 Episódio (`/e/:id/ouvir`)
- **Player** grande: play/pause, ±15 s, velocidade (0.75–2×), barra com waveform (pré-calculada no backend ou `AnalyserNode`), tempo em mono. Atalhos: `Espaço`, `←/→`.
- **Transcrição sincronizada**: a fala atual destaca; clicar numa fala pula o áudio (requer `turn_offsets` — opcional na fase 2; no MVP, lista simples sem sync).
- **Veredito** em destaque, acima da lista de ações (o resumo da checagem, para quem só quer o resultado).
- **Barra de ações:**
  - **Baixar MP3** (`?download=1`)
  - **Compartilhar** (ver §6)
  - **Copiar link**
  - **Roteiro (.md)** · **Verificação (.md)** · **Fontes (.md)**
  - **Novo episódio**
- Selo discreto: "Vozes sintéticas · Gerado com IA".
- Aviso de expiração: "Este episódio fica disponível por 24 h. Baixe para guardar."

### 5.5 Histórico (`/historico`)
Lista de episódios do `localStorage`, com estado "expirado" quando `404`.

### 5.6 Página pública `/s/{id}` (HTML do backend)
Mesma identidade visual (CSS inline mínimo, mesma paleta e fontes do sistema com *fallback* para serifa/sans do SO para não depender de requisições externas): título, resumo, veredito, player, link da(s) fonte(s), selo de vozes sintéticas, botão "Criar o seu".

## 6. Compartilhar (`lib/share.ts`)

Ordem de tentativa:
1. `navigator.canShare({ files })` → baixar o MP3 como `File` e `navigator.share({ files, title, text, url })`. (Android/iOS.)
2. `navigator.share({ title, text, url: shareUrl })` sem arquivo.
3. Fallback desktop (Brave/Chrome): menu com **Copiar link**, **WhatsApp** (`https://wa.me/?text=…`), **Telegram** (`https://t.me/share/url?...`), **E-mail** (`mailto:`), **X/Twitter** (`https://twitter.com/intent/tweet?...`).

Texto padrão: `🎙️ {título} — ouça o episódio: {shareUrl}` (sem hashtags).
Tratar `AbortError` (usuário cancelou) em silêncio; mostrar toast em outros erros.

## 7. Componentes (props e estados)

| Componente | Estados que devem existir |
|---|---|
| `Composer` | vazio, preenchido, inválido (URL), enviando, erro |
| `ConfrontoInput` | fechado (padrão), aberto/vazio, preenchido, inválido, removido |
| `ModeSwitch` | crítica, react (navegável por teclado, `role="radiogroup"`) |
| `ProgressStudio` | etapa (inclui confronto ou exame interno), `pct`, erro, acordando |
| `ScriptEditor` | leitura, editando, salvando, salvo, conflito |
| `VerificationPanel` | carregando, com itens (por status), vazio (não deveria ocorrer), destacado ao clicar na fala relacionada |
| `Player` | carregando, tocando, pausado, erro, buffer |
| `ShareMenu` | nativo, fallback, copiado |
| `Toast` | info, sucesso, erro (`aria-live="polite"`) |

## 8. Acessibilidade (checklist)

- Contraste AA em todos os textos e ícones informativos, **incluindo os selos de status do painel de verificação** (nunca só cor: usar também um rótulo de texto — "Apoiada", "Contestada" — e, se possível, um ícone).
- Todo controle com rótulo (visível ou `aria-label`); foco visível (anel `--amber` 2 px, offset 2).
- Navegação completa por teclado; ordem de tabulação lógica.
- Estados dinâmicos anunciados (`aria-live`) — progresso, erros, "copiado".
- Alvos de toque ≥ 44 px.
- `prefers-reduced-motion` respeitado; nunca só cor para transmitir informação (cor + ícone/texto).
- Textos de erro dizem o que fazer a seguir.

## 9. Copy (pt-BR, voz do produto)

Direta, calorosa, sem jargão. Exemplos:
- Vazio: "Cole um link ou um texto. O resto é com a gente."
- Confronto vazio: "Sem confronto, a IA examina a consistência interna da fonte."
- Carregando backend: "Acordando o estúdio… leva até um minuto na primeira vez."
- Erro de transcrição: "Esse vídeo não deixou a gente ler a transcrição. Cole o texto aqui e seguimos."
- Pronto: "No ar. Seu episódio está pronto."

## 10. Verificação visual (obrigatória antes de dar a UI como pronta)

Abrir no navegador e conferir **390×844** e **1280×800**: sem rolagem horizontal, sem texto cortado, hierarquia clara, estados vazios/erro/carregando todos olhados (incluindo o `ConfrontoInput` fechado e aberto, e o `VerificationPanel` com os quatro status). Corrigir e conferir de novo.
