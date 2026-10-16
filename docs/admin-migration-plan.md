# Atualização: CMS completo

A etapa descrita abaixo é o registro histórico da base administrativa. O estado atual e as evidências estão em `cms-completo.md`.

A migração aditiva `0003_cms_workspace` acrescenta seis tabelas: entradas editoriais, revisões, relações entre conteúdos, referências de mídia, desafios antispam e notificações. As tabelas anteriores permanecem disponíveis; autenticação, auditoria, mensagens e mídia são reutilizadas. Campos editoriais são validados por módulo antes de persistir snapshots JSONB. Relações entre registros e arquivos têm chaves estrangeiras.

O backup anterior ao CMS está em `docs/private/cms-backup/portfolio-before-cms.dump`; código anterior em `source-before-cms.zip`. O backup foi restaurado em `portfolio_cms_verify_20261014`, onde upgrade/downgrade/upgrade e verificação Alembic passaram. Nenhum downgrade foi executado no banco principal.

A importação usa UUIDs estáveis e não sobrescreve registros. Publicação em lote foi substituída por importação em rascunho após bloqueio de revisão automática. O leitor público combina a base estática aprovada com snapshots publicados; estados de retirada prevalecem sobre a base. Não se deve remover a base estática até revisar e publicar seus registros.

Reversão operacional: parar o worker novo e retornar os serviços ao código salvo, mantendo o esquema expandido. Isso preserva os dados editoriais, mas o código antigo exibe sua versão estática. Não executar downgrade no banco principal depois de editar conteúdos: ele elimina as seis tabelas novas. Para restaurar dados, criar primeiro nova cópia de segurança e restaurar em banco separado para inspeção.

---

# Plano de migração do CMS

## Inspeção e fronteira desta entrega

O pedido determina começar pela base administrativa. Esta etapa implementa autenticação, layout, dashboard de leitura e suporte de banco para autenticação. Os CRUDs e a troca das fontes públicas serão implementados depois dessa base, na ordem solicitada. Não foi reescrito o frontend público.

Estrutura inspecionada: Next.js App Router em `frontend/src/app`; componentes e dados locais em `frontend/src/components` e `frontend/src/data`; FastAPI em `backend/app`; PostgreSQL 16 e migração Alembic `0001`; Docker Compose com volumes separados de banco e mídia; proxy Nginx local em 8080. O esquema existente já contém 25 tabelas, incluindo conteúdo, mídias, contas, sessões e auditoria.

## Leitores, escritores e fontes atuais

| Conteúdo | Leitor atual | Fonte atual | Destino planejado |
|---|---|---|---|
| Hero, indicadores e textos institucionais | Home | `app/page.tsx` | `site_settings`, `pages`, `page_sections` |
| Projetos, serviços, artigos e vídeos planejados | Home | `data/home.ts` | `projects`, seções, `articles`, `videos` |
| Trajetória, skills, cases e biografia | Home, experiência, sobre, cases | `data/curriculum.json` | `experiences`, `experience_results`, `skill_categories`, `skills`, `cases`, páginas/configurações |
| Contatos | Formulário e canais | `data/contact.ts` | `site_settings` |
| Imagens e currículo público | Componentes Image e download | `frontend/public` | `media_assets` + volume persistente |
| Originais do currículo | Scripts de preparação | `docs/private` | Arquivo privado preservado |
| Administradores | CLI e API administrativa | PostgreSQL | Tabelas atuais reutilizadas |

Antes desta entrega, os escritores eram o CLI de administradores e o seed idempotente de quatro projetos/categorias. A nova API escreve somente sessões, contadores de tentativas, recuperação e auditoria. O dashboard apenas consulta conteúdo existente. Não foi importado conteúdo editorial nem alterado seu estado de publicação nesta etapa.

## Caminho de expansão

1. Preservar originais e capturar a Home em 1440/390 px.
2. Salvar backup PostgreSQL antes da migração. Restaurá-lo em um banco isolado e comparar todas as linhas das tabelas existentes.
3. Aplicar `0002` somente com duas tabelas novas: `auth_rate_limits` e `password_resets`. Reutilizar `admin_users`, `admin_sessions` e `audit_logs`.
4. Verificar upgrade, downgrade e novo upgrade exclusivamente no banco isolado. Aplicar a expansão no banco local; validar Alembic e autenticação.
5. Na próxima etapa, ampliar campos ausentes por migrações aditivas: vínculo atual explícito e término pendente, narrativa/anexos, duração de vídeo e campos editoriais necessários. Não inferir emprego atual a partir de término nulo.
6. Importar os dados existentes com identificador de origem e upsert que preserve edições. Importação inicialmente em rascunho, idempotente e com relatório de divergências. Revisar datas da Compass e confidencialidade dos cases.
7. Implementar módulos na ordem: currículo, skills, projetos, artigos, vídeos e contato, depois demais configurações. Validar uploads, revisão, sanitização do editor, preview autenticado e publicação antes de conectar o leitor público.
8. Substituir uma fonte pública de cada vez por um adaptador que entregue os mesmos dados e estruturas aos componentes existentes. Comparar screenshots antes/depois de cada troca. Não alterar classes, proporções, imagens ou composição para fazer a migração.
9. Só desativar uma fonte estática após validar sua equivalência, persistência, edição e rollback. Manter os originais; não executar contração destrutiva automaticamente.

O proprietário mantém a responsabilidade por validar dados profissionais e liberar cases confidenciais. Publicação editorial deve ser uma ação explícita do administrador, não um efeito do seed ou do deploy.

## Backup, compatibilidade e reversão

Backup desta etapa: `docs/private/admin-backup/portfolio-before-admin.dump`, formato custom do PostgreSQL, fora do frontend e ignorado pelo controle de versão. Sua restauração foi testada em `portfolio_admin_verify_20261014`; todas as linhas das 25 tabelas existentes foram preservadas após upgrade/downgrade/upgrade.

O backend anterior continua compatível com o esquema expandido porque nenhuma tabela antiga foi alterada. A reversão operacional preferida é retornar o código anterior e manter as duas tabelas novas. Não é necessário restaurar o banco ou apagar conteúdo para desativar o painel.

`alembic downgrade 0001` remove apenas as duas tabelas novas e perde seus tokens/contadores; use somente após parar os escritores novos e criar novo backup. Esse downgrade foi testado apenas na cópia isolada. Não executar downgrade da migração inicial no banco do portfólio. Uma restauração integral deve ser feita em banco separado para inspeção antes de qualquer troca.
