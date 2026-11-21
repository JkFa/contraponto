# 08 — Legal, ética e transparência

> Este documento orienta o produto; **não é aconselhamento jurídico**. Em caso de dúvida real, o dono do projeto deve consultar um advogado.

## 1. Princípios

1. **Examinar, não substituir.** O episódio confronta e verifica um material; não deve servir de substituto para ele.
2. **Fidelidade a cada fonte.** Nunca atribuir a uma fonte (primária ou de confronto) algo que ela não disse.
3. **Transparência.** Vozes sintéticas, uso de IA e o fato de haver (ou não) um material de confronto são sempre declarados.
4. **Crédito.** Todas as fontes usadas são sempre citadas com link.
5. **Imparcialidade entre fontes.** O material de confronto não é tratado como automaticamente mais confiável que a fonte primária, nem o contrário — o produto expõe a divergência, não arbitra quem está certo.
6. **Respeito.** Crítica ao argumento, não à pessoa.

## 2. Direitos autorais (Brasil)

- A transcrição de um vídeo, ou qualquer texto de terceiro, é obra protegida — **vale igualmente para a fonte primária e para o material de confronto**. O que **reduz** o risco é: não baixar nem reproduzir vídeo/áudio original de nenhuma das duas, parafrasear, citar pouco e creditar.
- A Lei 9.610/98, art. 46, III, admite **citação para fins de estudo, crítica ou polêmica, na medida justificada**, indicando autor e origem. O produto implementa isso assim:
  - **Máximo de 3 citações literais por fonte** (primária e confronto, contadas separadamente), cada uma com até **15 palavras** e timestamp.
  - O resto é **paráfrase** e **conclusão da verificação**, claramente marcada.
  - `sources.md` com autor, título, URL e data de acesso de **cada** fonte usada.
- "Zero risco" **não existe**: o conteúdo ainda pode ser contestado por qualquer um dos lados. O produto reduz o risco, não o elimina.
- Se o autor de qualquer uma das fontes pedir remoção: oferecer `DELETE /api/episodes/{id}` e orientar o usuário a retirar o episódio publicado.

## 3. YouTube e plataformas

- Não baixar mídia de nenhuma das duas fontes; usar apenas transcrição/legendas e metadados públicos (oEmbed).
- Respeitar os termos do YouTube: a transcrição é lida a pedido do usuário, para uso pessoal imediato; **não** fazer coleta em massa, cache longo ou redistribuição (cache só 24 h).
- Ao publicar o episódio no YouTube: preencher a divulgação de **conteúdo sintético/alterado** quando aplicável e evitar conteúdo repetitivo/em massa (política de conteúdo reutilizado).

## 4. IA e dados

- **Gemini free tier:** conteúdo enviado (fonte primária e confronto) pode ser usado para melhorar produtos da Google. Avisar na UI e não enviar material confidencial em nenhuma das duas entradas.
- Não registrar conteúdo dos usuários em log. Apagar episódios em 24 h.
- BYOK: chave guardada só no navegador; enviada por header; nunca logada.
- Sem rastreadores nem scripts de terceiros no frontend e na página `/s/{id}`.

## 5. O papel do material de confronto

- O usuário pode trazer qualquer material como confronto — inclusive um texto de opinião próprio. Isso **não** torna esse material imune à checagem: o protocolo de exame (`docs/04 §3`) aplica as mesmas regras de citação e fidelidade a ele.
- A IA nunca deve apresentar o resultado do confronto como um veredito definitivo e incontestável. O `verdict` é a conclusão **deste episódio**, com base no que foi apresentado — isso deve ficar textualmente claro no roteiro (ex.: "com base no que temos aqui…").
- Se o material de confronto for claramente de baixa qualidade (sem fonte, puramente opinativo, incompatível com o formato), o episódio deve dizer isso no diálogo em vez de tratá-lo como prova.

## 6. Vozes sintéticas

- Usar apenas vozes de catálogo (Edge-TTS/Piper). **Proibido** clonar voz de pessoa real ou imitar criador específico.
- Selo visível "Vozes sintéticas · Gerado com IA" no player, na página pública e nos metadados ID3.
- Os apresentadores têm nomes fictícios (padrão "Davi" e "Lia"); não personificar pessoas reais.

## 7. Música e assets

- Somente faixas **CC0** ou com licença que permita uso comercial e redistribuição.
- Registrar em `CREDITS.md`: título, autor, fonte (URL), licença, data. Sem registro, sem música.
- Fontes tipográficas: apenas as de licença aberta (OFL) via `@fontsource`.

## 8. Conteúdo sensível e abuso

- O prompt mestre proíbe ataque pessoal, especulação sobre intenções e afirmações sem respaldo — em relação a qualquer uma das duas fontes.
- Recusar/avisar em material (primário ou de confronto) que incite violência, discriminação ou envolva menores de forma imprópria; o roteiro deve ser rejeitado com mensagem clara (`CONTENT_REFUSED`).
- Sem promoção de desinformação: se uma fonte for ambígua ou duvidosa, o episódio diz isso — é exatamente para isso que existe o item `nao_verificavel`.
- Rate limit e limites de tamanho (por fonte) reduzem uso abusivo do backend gratuito.

## 9. Texto padrão (copiar para a UI, `sources.md` e página pública)

> **Episódio gerado com IA.** As vozes são sintéticas. O conteúdo examina "{título}", de {autor} ({url}){", confrontado com " + título do confronto se houver}. As conclusões são deste episódio e podem divergir das fontes originais.

## 10. Checklist de conformidade

- [ ] Máx. 3 citações literais por fonte, ≤ 15 palavras, com timestamp e `role` corretos
- [ ] `sources.md` gerado com autor, título, URL e data de cada fonte usada
- [ ] Selo de vozes sintéticas em player, página pública e ID3
- [ ] Aviso de privacidade do Gemini no Composer e no ConfrontoInput
- [ ] Nenhuma mídia do YouTube baixada ou armazenada (nenhuma das fontes)
- [ ] Música só com registro em `CREDITS.md`
- [ ] Nenhum conteúdo de usuário em logs
- [ ] `verdict` nunca apresentado como conclusão absoluta — linguagem de episódio, não de sentença
