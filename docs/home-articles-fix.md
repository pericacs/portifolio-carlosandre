# Artigos destacados na Home

## Diagnóstico

Home e `/artigos` já consultavam as publicações de `/api/content`, mas usavam flags diferentes: `featured` seleciona a Home; `spotlight` seleciona o destaque principal da listagem. Uma flag não implica a outra.

O schema compartilhava os objetos de campos entre módulos. A configuração específica de projetos mudava a aba de `featured` e `sortOrder` dos artigos para `SEO e publicação`, inexistente no editor de artigos. Reproduzido em Docker: ambos os controles estavam nessa aba inacessível. Assim, publicar e destacar na listagem não permitia controlar corretamente a Home pelo formulário.

A Home ainda limitava a seleção a três registros e incorporava metadados da lista antiga, embora a fonte dos registros já fosse o CMS.

## Correção

- Cópias independentes dos campos de artigos impedem a alteração pela configuração de projetos. Outros módulos não foram modificados.
- Aba Publicação: **Destaque na Home** (`featured`) e **Ordem de exibição na Home** (`sortOrder`, menor primeiro).
- A Home mostra todos os artigos publicados, visíveis, destacados e não planejados, sem limite oculto de três e sem metadados fixos. Empates de ordem usam slug para resultado determinístico.
- `spotlight` continua independente para o destaque principal em `/artigos`.
- Card, CSS, imagem, resumo, assuntos, título e link existentes foram mantidos. Nenhuma mudança nas seções de projetos, currículo, vídeos ou competências.
- Home explicitamente dinâmica; fetch do CMS e endpoint já usam `no-store`. Cada nova requisição lê o snapshot publicado, sem build/reinício ou invalidação manual de cache. Salvar rascunho não muda a versão pública: é necessário publicar a alteração revisada.

## Marcação inicial de O SPLIT DO MAL

A rotina `python -m app.feature_split_home` consulta somente o registro existente `o-split-do-mal`. A opção `--apply --expected-version N` marca o destaque em cada snapshot, sem alterar corpo, capa, ordem, status ou outras edições pendentes. Não cria artigo, não publica um rascunho e recusa artigo sem publicação, oculto/planejado ou com agendamento. Usa transação, bloqueio, conferência da versão e revisão/auditoria; repetir com a versão atual não gera alteração adicional.

A marcação foi testada localmente. **Não foi aplicada à produção:** o SSH configurado retornou `Permission denied (publickey,password)`. Nenhum comando remoto ou deploy foi executado.

Depois da atualização autorizada das imagens, no diretório do portfólio na VPS:

```bash
cd /opt/carlosandre-portfolio
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T backend python -m app.feature_split_home
```

Conferir o ID e copiar o número `version` retornado. Então executar, substituindo `N` por esse número:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T backend python -m app.feature_split_home --apply --expected-version N
```

Manter `RELEASE_TAG` conforme o procedimento de implantação já utilizado. Se houver edição concorrente, consultar novamente e revisar antes de repetir. Nenhum comando recria banco, volumes ou serviços do SmartFamily.

Pelo painel, a operação normal é abrir o artigo, aba Publicação, marcar Destaque na Home, ajustar a ordem, revisar e publicar. Ao retirar o destaque e publicar, o artigo sai da Home e continua disponível em `/artigos`.

## Verificação

Build Docker e TypeScript aprovados. Suíte PostgreSQL descartável: 116 testes aprovados, 20 ignorados pelas condições do ambiente (aviso de depreciação preexistente do TestClient), incluindo controles acessíveis, isolamento do schema, atualização idempotente da flag, proteção de versão e preservação de publicações/rascunhos.

Playwright em Docker usa o DOCX real (dez seções e quatro imagens), publica sem destaque, marca e ordena pelo painel, confirma que salvar rascunho não muda a Home e que publicar atualiza uma Home já visitada sem reinício. Testa cinco destacados, reordenação e retirada de destaque sem despublicar. Confere capa pública por SHA-256, título, descrição, assuntos e link; compara projetos, experiências, competências e vídeos.

Relatórios e capturas 1440/390 ficam em `.private`, fora do Git. Reprodução: construir as imagens de teste e executar `scripts/verify-production.py --home-articles`. Nenhum dado ou arquivo privado foi versionado.
