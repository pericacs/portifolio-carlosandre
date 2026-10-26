# Artigos recentes na Home — regra atual

A Home exibe automaticamente os **três artigos publicados mais recentes** da mesma fonte oficial de `/artigos`. Não exige marcação `featured` nem alteração manual de código. O artigo destacado na listagem continua também na grade cronológica.

A regra compartilhada usa a data editorial confirmada; quando ausente, utiliza o primeiro instante de publicação conhecido no CMS. Empates usam criação e ID, sem usar a última edição ou a prioridade manual. Registros sem data ficam ao final. Filtros e ordem são aplicados antes de limites/paginação.

No painel, conferir a data editorial, revisar e publicar. Salvar rascunho conserva a versão pública anterior. Republicar atualiza o conteúdo sem redefinir sua data inicial; despublicar retira o artigo das páginas públicas. O destaque principal da listagem é independente dos artigos recentes.

Não é necessário executar a antiga rotina de marcação inicial de O SPLIT DO MAL para fazê-lo aparecer na Home. Essa rotina permanece no histórico para compatibilidade, mas não é parte da publicação de artigos recentes.

Detalhes da auditoria de 26/10/2026, arquivos modificados, cache, testes e ressalva sobre a base do PR: [Relatório de recência e sincronização](artigos-recencia-sincronizacao.md).
