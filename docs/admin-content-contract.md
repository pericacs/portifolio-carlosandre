# Contrato de conteúdo para o futuro painel

Este documento descreve a integração editorial prevista. A base de autenticação e dashboard já está documentada em `admin-base.md`; edição e uploads descritos abaixo ainda não estão implementados.

## Fontes e edição

`frontend/src/data/curriculum.json` é a fonte normalizada das páginas públicas. Experiências, resultados, responsabilidades, tecnologias, cases, competências, formação, certificações e idiomas estão separados da apresentação. Os registros mantêm ordenação, destaque e referências de origem onde aplicável.

Na integração com a API, mapear experiências e resultados para suas entidades editoriais; mapear textos de apresentação, formação e idiomas para páginas/seções ou configurações apropriadas. Manter os identificadores estáveis para permitir edição sem recriar os registros. O contato público fica em `frontend/src/data/contact.ts`, evitando enviar todo o currículo ao componente cliente.

## Datas e publicação

- Datas do currículo têm precisão de mês. Não apresentar um dia inventado; eventual conversão para um campo SQL de data precisa preservar essa precisão na interface.
- `endMonth: null` com `endDateValidationRequired: true` significa data pendente, nunca emprego atual. Compass UOL exige confirmação do proprietário antes de alterar essa condição.
- Preservar períodos sobrepostos: não ajustar datas para produzir uma sequência artificial.
- Preservar a indicação de revisão editorial dos cases. A visualização local não autoriza publicação externa nem remoção automática das pendências.
- Não criar certificações, indicadores, artigos, vídeos ou URLs não fornecidos. Valores e resultados devem permanecer rastreáveis ao currículo ou a uma edição autorizada.

## Substituição do currículo

O original fica em armazenamento privado; o arquivo servido por `resume.publicDownload` é uma cópia pública revisada. A futura interface de upload deve permitir substituir o documento, mantendo revisão e histórico: validar DOCX, remover dados residenciais/metadados desnecessários da cópia pública, revisar datas e conteúdo, e só então trocar o vínculo público. Registrar autor e momento da alteração. Não servir o original privado automaticamente.

O currículo desta fase foi convertido por um mapeamento explícito de parágrafos em `scripts/prepare-curriculum.py`. Esse mapeamento é específico ao documento atual. Um DOCX substituto exige nova extração e revisão; não executar o mapeamento antigo silenciosamente em um documento diferente. Os scripts de preparação não são endpoints de upload.

Autenticação, autorização, armazenamento persistente, upload, auditoria e CRUD do painel continuam previstos para a Fase 4. A Fase 2 não modifica o banco nem as configurações de backend para antecipar essas funções.
