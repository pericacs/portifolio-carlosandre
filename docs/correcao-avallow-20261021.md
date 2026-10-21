# Correção pontual AVALLOW — 21/10/2026

Branch: `codex/avallow-card-fix`, derivada da implementação DOCX já concluída. Nenhum componente novo foi criado.

## Alteração

O terceiro card passa a exibir AVALLOW, a descrição “Infraestrutura financeira para crédito, automação e integração entre instituições.”, as tags Fintech / Crédito / Infraestrutura e o status Em desenvolvimento.

A imagem fornecida foi copiada sem edição, moldura ou sobreposição. SHA-256 da origem e do arquivo público: `a1436552052ea70e34bd4f4da68d0c803eca93473fdae0d5c9077807e046b55a`. A apresentação usa o enquadramento existente, com `object-fit: cover` exclusivamente neste card: preserva a proporção da imagem e recorta as bordas para caber na mesma janela dos demais cards. Não há distorção nem alteração da altura dos outros cards.

A faixa reutiliza o mesmo elemento, classes e objeto de propriedades do Beloria. O estágio do AVALLOW vem de `developmentStage`, campo já existente no CMS. Nenhuma alteração de schema ou migração foi necessária.

## Arquivos

- `frontend/public/images/avallow-fintech.png`: imagem original fornecida.
- `frontend/src/data/avallow.json`: cinco campos do card, também utilizados pela atualização pontual do CMS.
- `frontend/src/lib/public-content.ts`: apresentação inicial aprovada do registro OnStar como AVALLOW; publicações do CMS continuam sobrepondo essa apresentação normalmente.
- `frontend/src/app/page.tsx`: leitura do estágio do AVALLOW, reaproveitando a faixa existente.
- `frontend/src/app/globals.css`: regra restrita à imagem do AVALLOW; sem alteração de regras globais de espaçamento, fonte ou responsividade.
- `scripts/update-avallow.py`: atualização controlada somente do rascunho correspondente, com versão esperada, auditoria, revisão e dry-run por padrão.
- `scripts/verify-avallow.py` e `frontend/tests/avallow-card.spec.cjs`: ensaio isolado PostgreSQL/CMS e comparação visual.
- Este relatório.

O baseline de 117 registros e os pacotes editoriais privados não foram modificados.

## Persistência e histórico

O registro local tinha título OnStar SCD, versão 1 e estado rascunho. Foram alterados exclusivamente `title`, `description`, `tags`, `developmentStage` e `cover`. Agora está na versão 2, ainda como **rascunho, sem publicação**. O ID, `source_key`, slug `onstar-scd`, conteúdo detalhado, `_legacy` e revisão inicial permanecem. Há duas revisões, incluindo `update_avallow_card`. Os demais projetos não foram atualizados.

A imagem é um asset público versionado; sua referência `/images/avallow-fintech.png` fica no PostgreSQL. Alterações futuras de imagem, descrição, tags e estágio continuam disponíveis no painel existente. Não é necessário criar um novo projeto nem excluir o OnStar.

## Validação

- Build Docker Next.js e TypeScript: aprovados.
- Ensaio Playwright em PostgreSQL descartável: aprovado.
- Atualização idempotente: segunda execução retorna `already_updated`, sem nova revisão.
- Salvamento e publicação pelos endpoints existentes do CMS: aprovados, exclusivamente no banco descartável; os cinco campos persistem em `published_data`.
- Revisão inicial, `_legacy` e slug OnStar preservados.
- Outros três projetos mantêm suas versões, conteúdo HTML, posições e dimensões.
- Ordem: SmartFamily, Beloria, AVALLOW, Orquestrador IA.
- Estilo computado da faixa do AVALLOW igual ao Beloria, imediatamente abaixo da imagem.
- Capturas de página inteira e da seção em **1440 px** e **390 px**, sem overflow.
- Comparação antes/depois: **zero pixels alterados fora do AVALLOW**, nas duas larguras. Hero e demais seções ficaram idênticos no ensaio.
- Inspeção visual desktop/mobile: aprovada. Não houve modificação de fotografia, outros assets ou componentes.

Evidências privadas: `.private/portfolio-avallow-7044a3d178/` (`before-*`, `after-*`, `report.json`). Os recursos Docker descartáveis foram removidos ao terminar. O teste compara builds anterior/posterior com o mesmo baseline isolado; não faz escrita em bancos de outros projetos.

## Reprodução e pendências

```powershell
docker build -t carlosandre-avallow-check-frontend frontend
python scripts/verify-avallow.py
```

O ensaio utiliza a imagem anterior `carlosandre-docx-check-frontend` e o backend `carlosandre-docx-check-backend`, já construídos na etapa anterior. Playwright/Sharp devem estar disponíveis no Node, ou indicados por `PLAYWRIGHT_MODULE` / `SHARP_MODULE`.

Não houve deploy, acesso à VPS, reinício de serviços existentes ou mudança em SmartFamily/Beloria. Para disponibilizar na VPS posteriormente, revisar este commit, atualizar somente a imagem frontend do portfólio com o asset novo e aplicar os cinco campos ao registro existente no PostgreSQL de destino. Se houver importação do pacote editorial anterior, aplicar esta correção **depois** dela, pois o pacote não foi alterado nesta tarefa.

O utilitário abaixo roda somente no Docker selecionado; por padrão apenas mostra o plano. Conferir o container e a versão atual antes de usar. Não executar contra outro projeto:

```powershell
python scripts/update-avallow.py --container CONTAINER_BACKEND_DO_PORTFOLIO --expected-version VERSAO_ATUAL
# Somente após revisão do plano:
python scripts/update-avallow.py --container CONTAINER_BACKEND_DO_PORTFOLIO --expected-version VERSAO_ATUAL --apply
```

Depois de revisar no painel, publicar o AVALLOW pela ação normal do CMS. O utilitário não publica. Os comandos de destino e a publicação definitiva não foram executados. A atualização local do rascunho foi autorizada pelo pedido e concluída sem afetar os demais registros.
