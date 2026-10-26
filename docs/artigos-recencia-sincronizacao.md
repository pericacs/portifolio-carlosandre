# Recência e sincronização dos artigos — homologação de 26/10/2026

## Diagnóstico confirmado antes da edição

A auditoria na Hostinger usou apenas consultas de metadados em transações `SET TRANSACTION READ ONLY`, revisão de publicação e GETs públicos. Nenhum arquivo, conteúdo, serviço, banco ou credencial foi alterado na VPS.

- Origem `/api/content`: artigos seguiam `published_data.sortOrder`; não havia uma regra cronológica compartilhada.
- Home: filtrava `featured` e ordenava apenas pela string `publishedDate`. O novo artigo estava com esse campo vazio e era mandado para o final. O HTML da origem mostrava quatro cards, com ele em quarto lugar.
- `/artigos`: preservava a ordem manual da API; `ArticleListing` retirava o artigo `spotlight` da grade normal, embora continuasse no bloco Em destaque.
- Publicar novamente sobrescrevia `cms_entries.published_at`; portanto a coluna isolada podia representar a última republicação, não a publicação inicial.

### Data real do novo artigo

O registro **O golpe de R$ 813 milhões não precisou de hacker** estava publicado, visível, não planejado, com `featured=true`, `spotlight=true`, `publishedDate` vazio e três revisões de publicação. A primeira revisão de publicação é **25/10/2026 03:59:08 UTC** (00:59:08 em São Paulo); `published_at` atual é **26/10/2026 12:30:12 UTC**, após republicação.

A ordem efetiva validada com os metadados existentes é:

| Artigo | Data para recência | Fonte |
|---|---|---|
| O golpe de R$ 813 milhões não precisou de hacker | 25/10/2026 | Primeira publicação registrada, sem data editorial preenchida |
| O SPLIT DO MAL | 19/10/2026 | Data editorial confirmada |
| Engenharia de dados aplicada ao Split Payment do Bem | 13/10/2026 | Data editorial confirmada |
| Split Payment do bem e Split Payment do mal | 07/10/2026 | Data editorial confirmada |

Não houve preenchimento ou correção automática de registros na produção.

## Modelo, regra e endpoints

`cms_entries` mantém `data` (edição), `published_data` (snapshot público), `status`, `published_at`, `created_at`, `updated_at`, `deleted_at` e `version`. `featured`, `spotlight`, `publishedDate` e `sortOrder` ficam nos JSONB, sem coluna física `sort_order`. `cms_revisions` guarda os eventos de publicação. Nenhuma migração de schema foi necessária.

A regra única está em `backend/app/article_publications.py`:

1. Exige snapshot publicado, registro não excluído/não arquivado, visível e não planejado. Rascunho novo e agendamento ainda não publicado não aparecem. Uma edição pendente não retira o snapshot público anterior.
2. Usa a data editorial ISO confirmada no snapshot. Se ausente, utiliza o instante mais antigo conhecido entre revisão de publicação e `published_at`. Não inventa data a partir da criação ou da última edição.
3. Ordena no PostgreSQL por data efetiva decrescente, nulos por último, `created_at DESC` e `id DESC`. Só então aplica `LIMIT/OFFSET`. Datas editoriais sem hora são normalizadas em UTC; o fallback conserva o instante registrado.
4. Sem data em nenhuma fonte, o registro permanece no final com desempate determinístico, sem modificar seus dados.
5. Republicação de artigos preserva o primeiro instante conhecido. Os demais módulos continuam com seu comportamento anterior.

`GET /api/content` utiliza essa regra para `modules.artigos`, preservando os outros módulos. `GET /api/articles?limit=20&offset=0` oferece a mesma sequência paginada, com `items`, `total`, `limit` e `offset` (limite entre 1 e 100).

## Frontend e painel

- `public-content.ts` não reinterpreta a ordem dos artigos: Home recebe os três primeiros da sequência oficial; `/artigos` e páginas internas usam a mesma coleção elegível.
- A Home não exige `featured`: todo novo artigo publicado pode entrar automaticamente conforme a recência. O limite é aplicado depois da ordenação.
- `spotlight` continua controlando o bloco Em destaque, sem retirar o artigo da grade cronológica e sem alterar a ordem. Nenhuma flag existente foi modificada.
- Capas, títulos, resumos, assuntos, tags e links continuam nos componentes `HomeArticleCard`, `ArticleCard` e `ArticleLink`. Nenhum CSS, asset ou conteúdo editorial foi substituído.
- Os textos dos dois controles legados e a orientação da aba Publicação esclarecem que marcação/ordem manual não definem os artigos recentes. Login, sessões, CSRF, editor e publicação permanecem funcionais.

## Cache e consultas

A auditoria HTTPS de `/`, `/artigos` e `/api/content` retornou HTTP 200, `CF-Cache-Status: DYNAMIC`, sem `Age`. HTML usa `private, no-cache, no-store, max-age=0, must-revalidate`; API usa `no-store`.

A política existente foi preservada: fetch público `no-store`, Home dinâmica e memoização React apenas dentro da renderização. Não foram desativados caches de outras áreas nem criados webhooks ou tarefas de invalidação. A próxima requisição após publicar, republicar ou despublicar lê o snapshot atual. Salvar uma edição pendente não a torna pública.

As páginas continuam fazendo uma única chamada pública compartilhada ao CMS; a seleção de artigos usa uma consulta SQL ordenada com agregação das revisões, sem consulta por artigo. A listagem visual existente não ganhou paginação ou controles novos; a paginação foi validada no endpoint público.

## Arquivos desta correção

| Arquivo | Alteração |
|---|---|
| `backend/app/article_publications.py` | Elegibilidade, recência, histórico e paginação compartilhados |
| `backend/app/cms.py` | Integração nos endpoints e preservação da publicação inicial de artigos |
| `backend/app/cms_schema.py` | Textos dos controles legados, sem mudar valores ou schema |
| `frontend/src/lib/public-content.ts` | Preserva ordem oficial e seleciona os três recentes |
| `frontend/src/app/artigos/page.tsx` | Consome a coleção oficial |
| `frontend/src/app/artigos/[slug]/page.tsx` | Mesma coleção para detalhe e relacionados |
| `frontend/src/components/articles/listing.tsx` | Destaque permanece também na grade |
| `frontend/src/components/cms/workspace.tsx` | Orientação mínima da publicação automática |
| `backend/tests/test_article_publications.py` | Datas, histórico, desempate, paginação, rascunhos e sincronização |
| `backend/tests/test_articles.py` | Contrato dos controles do painel |
| `frontend/tests/home-article-order.spec.cjs` | Fonte única, três recentes, sem filtro por destaque nem reordenação local |
| `frontend/tests/home-articles.spec.cjs` | Fluxo completo de artigos e comparação das demais seções |
| `frontend/tests/docx-import.spec.cjs` | Home pode ganhar legitimamente o artigo publicado no teste |
| `docs/home-articles-fix.md` | Instruções atualizadas para a regra atual |
| `docs/artigos-recencia-sincronizacao.md` | Diagnóstico, auditoria e resultados |

## Testes e resultados

- Dockerfiles de produção backend/frontend: build aprovado; TypeScript integrado ao build Next aprovado.
- Pytest em PostgreSQL 16 descartável: **121 aprovados, 20 ignorados** por condições do ambiente. Aviso preexistente de depreciação do TestClient.
- Regressões SQL: datas confirmadas, fallback à primeira publicação, timestamp legado anterior, nulos no final, empate por criação/ID, ordem antes da paginação, exclusão de inéditos/arquivados/ocultos/planejados, snapshot público durante edição, atualização e despublicação.
- Leitor frontend real: passa a sequência da API sem reordenar, não exige featured, limita a três, preserva os cards/demais módulos e usa apenas uma chamada `no-store`.
- Playwright: publicar artigo sem data editorial/sem featured coloca-o automaticamente na Home; destaque aparece no bloco e na grade; edição no painel conserva o snapshot até publicar; republicação mantém a data inicial; mudanças de flags/ordem não mudam recência; despublicação atualiza ambas as páginas; paginação reproduz a sequência integral.
- Capturas 1440/390 da Home e listagem revisadas. Conteúdo, imagens, links e estilos de projetos, experiências, competências e vídeos permaneceram iguais no ensaio.
- Regressão DOCX/produção isolada aprovada: dez seções, quatro imagens, recriação de container, expiração, idempotência, recuperação, backup/restauração descartáveis e rollback dirigido de dados de controle.
- Sintaxe Python por AST (26 arquivos), sintaxe Node dos testes e `git diff --check` aprovados. O repositório não fornece comando/configuração de ESLint/Ruff/Flake8; não foi declarado um lint inexistente como executado.

Documento de homologação, relatórios, credenciais sintéticas e screenshots ficaram apenas em `.private`, fora do Git. Nenhum dado fictício foi criado em produção.

## Branch, PR e pendências

A branch `codex/articles-recency-sync` foi criada de `origin/main` atualizado, que ainda apontava para `374533a93aec30b2d9509652398cc94ee3a8bd79`. Para preservar a aplicação atualmente implantada, recebeu por fast-forward a história de produção até `8a39d8d257822306601edf10e55cf8467b91a9cb`, antes desta correção.

**O PR para main contém também 15 commits anteriores que já estavam em produção e ainda não integrados em main.** A revisão específica desta tarefa deve comparar `8a39d8d..codex/articles-recency-sync`. Main e branches anteriores não foram reescritos. Nenhum merge remoto, push forçado ou deploy foi realizado.

Pendências de homologação: revisar essa base histórica e os commits novos; depois da aprovação e de uma implantação controlada, validar no domínio a ordem e as capas reais. A auditoria remota nesta etapa foi somente de leitura. SmartFamily, AVALLOW e serviços/volumes da VPS não foram alterados.

Commit de implementação e regressões: `0c126c621f74c6f128161362acbecd631117c158`.
