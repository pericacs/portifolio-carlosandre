# CMS completo — entrega local

## Acesso e conteúdo

- Site: http://localhost:8080/
- Painel: http://localhost:8080/admin
- Autenticação existente preservada. Não foi criada senha padrão nem alterada a conta do proprietário.
- 117 registros importados como rascunhos; segunda execução importou zero. Nenhuma edição existente é sobrescrita.
- A versão aprovada do site permanece como base pública. A API entrega apenas snapshots publicados; publicar substitui o registro correspondente. Arquivar, excluir ou despublicar retira o conteúdo correspondente. Rascunhos nunca chegam ao leitor público.
- Compass UOL permanece com término pendente de validação. Cases exigem revisão de confidencialidade. Currículo exige revisão de dados pessoais antes da publicação. Originais privados preservados.

## Módulos entregues

| Área | Rotas administrativas |
|---|---|
| Identidade e currículo | `/admin/perfil`, `/admin/experiencias`, `/admin/formacoes`, `/admin/certificacoes`, `/admin/idiomas`, `/admin/curriculo` |
| Competências | `/admin/skills`, `/admin/categorias` |
| Portfólio | `/admin/projetos`, `/admin/cases` |
| Conteúdo | `/admin/artigos`, `/admin/videos`, `/admin/midia` |
| Negócios | `/admin/mensagens` |
| Plataforma | `/admin`, `/admin/configuracoes`, `/admin/auditoria`, `/admin/seguranca` |

Formulários compartilhados em abas, pesquisa, filtros, paginação, ordenação, visibilidade, feedback e proteção contra perda de alterações. O editor de artigos possui PT/EN, imagens, links, listas, títulos e tabelas. Galerias e diagramas podem ser reordenados. SEO global e por conteúdo. Publicações ficam disponíveis nas rotas públicas de detalhes de projetos, cases, artigos e vídeos.

Salvar não altera a versão publicada. Agendar captura uma versão independente de futuras edições. O worker consulta os agendamentos a cada 15 segundos. Histórico permite restaurar um rascunho sem alterar a publicação. Consultas públicas usam `no-store`, evitando cache desatualizado.

Uploads PNG/JPEG/WEBP/PDF/DOCX ficam no volume persistente, com nomes aleatórios, limite de 8 MB e validação do formato. Arquivos não publicados exigem autenticação. Referências impedem exclusão de mídia em uso. HTML é sanitizado no backend; URLs do YouTube têm validação de domínio e identificador. Autenticação, CSRF, rate limiting, transações e auditoria são reutilizados.

O formulário de contato grava mensagens no PostgreSQL, com consentimento, proteção antispam, fila de notificação e retenção configurável. O painel permite pesquisa, status, notas internas e CSV protegido contra fórmulas.

## Validação

- Build de produção Next.js e TypeScript concluídos.
- 49 testes de API passaram no PostgreSQL real, usando reversão das transações de teste. Um aviso de depreciação do adaptador HTTP de testes permanece; nenhum teste falhou.
- Migração `0003`: restauração do backup, upgrade, downgrade para `0002`, novo upgrade e `alembic check` sem diferenças, exclusivamente no banco temporário.
- Playwright: 16 telas em 1440 e 390 px, capturas adicionais de editores e Home; CRUD de projeto, upload, preview autenticado, isolamento de rascunho, publicação e arquivamento; artigo no editor visual; contato público chegando ao atendimento administrativo.
- Evidência e resultados: `docs/screenshots/cms/playwright-report.json`. Capturas em `docs/screenshots/cms/`.
- Comparação visual automatizada da Home antes da seção de contato: posição das seções preservada; tolerância inferior a 0,01% dos canais de imagem. O formulário mantém a composição e agora confirma recebimento pelo backend.
- As contas e os conteúdos criados pelo Playwright são temporários e removidos ao fim da execução.

## Arquivos principais

Backend: `app/cms.py`, `app/cms_schema.py`, `app/cms_dashboard.py`, `app/worker.py`, `app/import_cms.py`, `app/models.py`, `app/main.py`, `app/admin.py`, `app/data/cms_initial.json`, `alembic/versions/0003_cms_workspace.py`, `tests/test_cms.py`, `tests/test_admin.py`, `requirements.txt`.

Frontend: `src/components/cms/`, `src/app/admin/`, `src/lib/public-content.ts`, `src/data/cms-initial.json`, integrações nas páginas públicas e componentes da Home; `tests/cms.spec.cjs`.

Infraestrutura: `compose.yaml` inclui worker; `infra/nginx/` resolve serviços Docker novamente após recriação. Importação: `scripts/build-cms-import.cjs`. Backups privados: `docs/private/cms-backup/`.

## Operação e limites

```powershell
docker compose up -d --build
docker compose exec backend python -m app.import_cms
docker compose exec backend python -m pytest -q -p no:cacheprovider
docker compose exec backend alembic check
```

Para o Playwright, disponibilize `playwright` e `sharp` no Node ou informe os caminhos dos pacotes em `PLAYWRIGHT_MODULE` e `SHARP_MODULE`, e execute `node frontend/tests/cms.spec.cjs` da raiz. Execute em desenvolvimento: a suíte publica registros claramente identificados como QA e os remove depois.

SMTP não está configurado; envio real de e-mail não foi validado. A fila envia notificações para CONTACT_NOTIFICATION_EMAIL quando o SMTP estiver configurado. Consulte contato-gmail.md. Analytics e YouTube Data API estão preparados como pontos de integração, sem ativação ou credenciais inventadas. Não houve deploy externo nem alteração de DNS/TLS.

A revisão automática bloqueou a proposta inicial de publicar a importação em lote; a alternativa implementada importa somente rascunhos e preserva a base aprovada. A publicação depende da ação explícita do administrador no painel.


## SmartFamily — 15/10/2026

Cadastro de projetos ampliado com as sete abas solicitadas: informações gerais, imagens e mídia, funcionalidades, arquitetura e tecnologias, links e acessos, resultados e roadmap, SEO e publicação. Histórico permanece em aba própria.

Cada campo de conteúdo pode ser PÚBLICO ou PRIVADO. Anotações internas são sempre privadas. O backend remove campos privados antes de persistir a versão pública e antes de entregar a API pública. Referências de mídia privadas não concedem acesso anônimo; tornar uma imagem privada e republicar retira seu acesso público, salvo se outro conteúdo publicado ainda usar o mesmo arquivo. Preview autenticado mostra somente os campos que seriam públicos. A revisão de publicação inclui documentos e imagens: o sistema não faz OCR para descobrir segredos dentro de arquivos.

A página `/projetos/smartfamily` recebeu somente nome, categoria, descrição, funcionalidades, tecnologias, integrações e URLs fornecidos pelo proprietário. Não foram inventados resultados, datas de roadmap ou screenshots do produto. Campos e uploads estão prontos para recebê-los. Vídeos e documentação externa são cadastrados por links; documentação PDF/DOCX pode ser enviada ao armazenamento persistente. O cartão da Home preserva sua apresentação aprovada; os novos detalhes alimentam a página interna.

Não houve mudança no esquema PostgreSQL: o contrato validado utiliza as entradas JSONB e revisões existentes. `backend/app/register_smartfamily.py` cadastra uma única vez, preserva o rascunho anterior e publica exclusivamente os fatos fornecidos. Execuções posteriores não sobrescrevem edições.

Arquivos alterados nesta etapa: `backend/app/cms_schema.py`, `backend/app/cms.py`, `backend/app/register_smartfamily.py`, `backend/tests/test_smartfamily.py`, `frontend/src/components/cms/api.ts`, `workspace.tsx`, `preview.tsx`, `public-detail.tsx`, `frontend/src/lib/public-content.ts` e `frontend/tests/cms.spec.cjs`.

Validação: build Next.js/TypeScript e 56 testes de API no PostgreSQL passaram. Novos testes verificam isolamento dos dados privados, acesso autenticado a arquivos, publicação/reclassificação de imagens, permissões e rejeição de padrões de segredos, IPs privados e links internos. Capturas reais: `docs/screenshots/cms/smartfamily-admin-{1..7}-{1440,390}.png` e `smartfamily-public-{1440,390}.png`.


## Reestruturação visual SmartFamily — referência fornecida

Referência preservada em `docs/references/smartfamily-aprovado.png`. Apresentação exclusiva em `frontend/src/components/smartfamily/presentation.tsx` e `smartfamily.module.css`, selecionada apenas na rota `/projetos/smartfamily`. Nenhuma alteração no menu global, na Home ou na apresentação dos outros projetos.

A página contém hero com composição desktop/mobile, visão geral, problema, solução, funcionalidades, fluxo e exemplos de comandos, galeria, arquitetura, stack, integrações, desafios, roteiro de validação, vídeo, links e CTA. Ilustrações são componentes HTML/CSS e ícones vetoriais, explicitamente identificados. Não são capturas do sistema SmartFamily nem comprovam funcionamento. A referência orientou composição, hierarquia, cartões claros e detalhes azul/violeta; as seções adicionais seguem a mesma linguagem.

Conteúdo estruturado: `backend/app/smartfamily_schema.py` e `smartfamily_content.py`. Blocos e mídias usam as entradas JSONB e revisões PostgreSQL existentes. Cada bloco possui texto rico, status, evidência, ordem e visibilidade. Cada mídia tem posição, título, descrição, texto alternativo, ordem, arquivo persistente ou vídeo do YouTube, indicação de ilustração e visibilidade. Os oito espaços específicos são capa, desktop, agenda, tarefas, WhatsApp, mobile, arquitetura e vídeo. O editor está em `frontend/src/components/cms/smart-fields.tsx`. Preview autenticado usa a mesma apresentação pública, removendo conteúdo privado.

Status disponíveis: Implementado, Em desenvolvimento, Planejado e Não verificado. Publicar como Implementado exige registrar evidência; a responsabilidade por validar essa evidência permanece com o editor. Nenhuma capacidade foi marcada como concluída sem comprovação. Comandos são exemplos ilustrativos porque não foram fornecidos testes reais. O roadmap publicado é um roteiro de validação, sem datas ou compromissos de entrega inventados.

Validações: 60 testes de API passaram, incluindo blocos privados, sanitização, publicação, imagens privadas/públicas, ordenação e status. Build Next.js/TypeScript passou. Playwright percorreu módulos e fluxos CMS, capturou as 11 abas SmartFamily, preview autenticado e página completa em 1440 e 390 px. Comparação da Home manteve as posições e a diferença residual anterior de rasterização (510/102 canais antes da seção de contato). A página passou nas verificações de seções, links conhecidos, carregamento, rótulos de ilustração, ausência de erros JavaScript e ausência de overflow horizontal.

Capturas: `docs/screenshots/cms/smartfamily-public-1440.png`, `smartfamily-public-390.png`, `smartfamily-hero-1440.png`, `smartfamily-hero-390.png`, `smartfamily-admin-{1..11}-{1440,390}.png`. Material de produto real e confirmação funcional permanecem pendentes de fornecimento pelo proprietário.


## HTML final aprovado — integração local

Fonte: `C:/Users/T-GAMER/Downloads/SmartFamily_Final (1).html`. A página existente continua em `/projetos/smartfamily`; os dados continuam nas entradas, snapshots e revisões PostgreSQL do CMS. Nenhum HTML isolado substituiu o aplicativo. O cabeçalho e o rodapé usam a identidade e a navegação do portfólio. Os demais projetos mantêm seu renderizador anterior.

Foram extraídos 11 arquivos originais (logo, dashboard, mapa e oito capturas), sem recortar ou reprocessar imagens. O manifesto registra hashes SHA-256. Assets de origem ficam em `backend/app/data/smartfamily-final/`; a importação os registra na biblioteca e no volume persistente de mídia. Nenhuma string base64 foi incorporada aos componentes. As oito transcrições permanecem iguais ao array aprovado no HTML; a lista Sua família conserva somente os cinco itens aprovados, inclusive na imagem original.

A versão reúne apresentação, resumo, problema/solução, funcionalidades, canais, oito demonstrações, fluxo, mapa, arquitetura, integrações, decisões, perguntas frequentes, evolução e acesso ao aplicativo. Calendários externos continuam descritos como escopo de integração, não como entrega comprovada. O mapa permanece identificado como visão ilustrada, não topologia de produção verificada.

### Arquivos desta atualização

- `scripts/extract-smartfamily-final.py`: parser do arquivo fornecido, extração sem executar scripts e manifesto de integridade.
- `backend/app/smartfamily_final.py`: campos editoriais, sanitização, validação das demonstrações e importação idempotente com revisões.
- `backend/app/cms_schema.py`, `backend/app/cms.py`: integração ao contrato, publicação e referências de mídia existentes.
- `backend/app/data/smartfamily-final/`: conteúdo extraído, manifesto e 11 arquivos originais.
- `frontend/src/components/smartfamily/final-presentation.tsx`, `final-interactions.tsx`, `final.module.css`: layout aprovado, conteúdo renderizado no servidor, filtros e visualizador de imagem completa.
- `frontend/src/components/smartfamily/project-footer.tsx`, `presentation.tsx`, `frontend/src/app/projetos/[slug]/page.tsx`: integração exclusiva da rota e rodapé do portfólio.
- `frontend/src/components/cms/final-demos.tsx`, `fields.tsx`, `workspace.tsx`: edição das seções, transcrições, imagens, ordem e visibilidade no painel existente.
- `backend/tests/test_smartfamily_final.py`, `frontend/tests/smartfamily-final.spec.cjs`, `cms.spec.cjs`, `smartfamily-public.spec.cjs`: validações e atualização das expectativas após aprovação da nova versão.

### Verificações

Build Next.js/TypeScript aprovado; 62 testes de API passaram no PostgreSQL. Playwright validou desktop (1440 px) e celular (390 px), oito transcrições, hashes dos 11 arquivos servidos, filtros (Todos 8 / Agenda 3 / Tarefas 2 / Financeiro 2 / Família 1), fonte de 12 px e line-height de 18 px, celulares de 260 px, ausência de overflow horizontal, carregamento das imagens, modal, fechamento por botão e Escape, foco dentro do modal e retorno ao acionador. Conteúdo principal e oito demonstrações também verificados com JavaScript desativado. Há apenas o aviso de depreciação já conhecido do adaptador HTTP dos testes Python.

Evidências: `docs/screenshots/cms/smartfamily-final-report.json`; página completa em `smartfamily-final-1440.png` e `smartfamily-final-390.png`; hero em `smartfamily-final-hero-{1440,390}.png`; visualizador em `smartfamily-final-modal-{1440,390}.png`. A fonte HTML foi comparada visualmente com a estrutura integrada; a adaptação preserva o cabeçalho/rodapé globais do portfólio.

Não houve publicação em produção. A disponibilidade funcional dos serviços externos não foi auditada; os links oficiais fornecidos foram preservados. As capturas documentam o comportamento mostrado, sem extrapolar resultados ou afirmar sincronização externa não demonstrada.
