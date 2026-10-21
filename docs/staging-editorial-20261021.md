# Ensaio editorial local e transferência manual — 21/10/2026

Nenhum acesso à VPS, transferência, importação em produção ou deploy foi executado nesta etapa. Os comandos abaixo são para execução humana posterior. SmartFamily, Nginx, DNS e Cloudflare não participaram do ensaio.

## Pacote revisado

O pacote originalmente aprovado, `editorial-transfer-20261021T041601Z.tar.gz`, SHA-256 `e1d7df9b210248436bf2922490b6357189a2087184d2629cd418b44ae6690e3e`, permanece intacto. **Não transferir essa versão:** o ensaio PostgreSQL revelou duas incompatibilidades no importador que os testes offline não detectaram:

1. O reconhecimento de seed retinha campos brutos que `app.import_cms` descarta ao validar nove experiências. Foi ajustado para reproduzir exatamente a validação do seed, mantendo `_legacy`.
2. A verificação de operações usava `rowcount`, que pode retornar -1 com psycopg e INSERT RETURNING. Agora verifica a quantidade de IDs explicitamente retornados por INSERT/UPDATE/DELETE.

Novo arquivo privado: `C:\Portifolio - Carlos Andre\.private\editorial-transfer-20261021T042605Z.tar.gz`.

SHA-256: `60812da2f38caa50b9a52fb04b07ab4a7689f78fde5538713b82fe848acd69c3`.

Package ID: `28d148d5810b0d3350e10ac468f933003335c98b139289c80ca42b55b9686050`.

O JSON editorial, baseline, README e as 28 mídias são idênticos aos originais. Somente `tools/editorial_transfer.py`, manifesto e catálogo de hashes mudaram. O hash novo deve ser conferido antes da transferência manual. A versão intermediária `042519Z` também está superada.

## Conteúdo

| Módulo | Quantidade |
|---|---:|
| Configurações | 1 |
| Experiências | 9 |
| Skills | 74 |
| Categorias | 7 |
| Formações | 1 |
| Certificações | 1 |
| Idiomas | 2 |
| Currículo | 1 |
| Projetos | 4 |
| Cases | 9 |
| Perfil | 1 |
| Artigos | 8 |
| Vídeos | 4 |
| **Total CMS** | **122** |

Estados: 118 rascunhos e 4 publicações, sem republicação automática. Inclui os cinco artigos adicionais, perfil atualizado e apresentação ampliada do SmartFamily. Mídias: 28 arquivos, 17 PNG e 11 WebP, 9.231.754 bytes. Há 138 revisões, 74 vínculos de conteúdo e 56 referências de mídia. O pacote contém 429 linhas editoriais em 25 tabelas; não confundir esse total com os 122 conteúdos CMS.

## Ensaio e limites

Harness: `scripts/test-editorial-staging.py`. Usa imagem backend local `carlosandre-production-check-backend`, PostgreSQL 16 Alpine, rede Docker interna aleatória, nenhum mapeamento de porta e volumes aleatórios exclusivos para banco, mídia e plano. APP_ENV=production é usado somente para exercitar as proteções do importador com credenciais sintéticas. Não lê o `.env` local nem monta o banco ou uploads originais.

Alembic até 0003 e o seed real de 117 conteúdos são executados somente nos bancos descartáveis. Os cenários cobrem destino com seed e destino vazio, planejamento somente de leitura, aplicação, comparação integral das 25 tabelas com o pacote, estados editoriais, FKs e 28 hashes no volume Linux; repetição sem alteração do recibo ou conteúdo; rollback para o hash anterior e segunda reversão sem escritas. Um terceiro banco recebe um trigger de falha intencional na gravação do recibo: toda a transação deve ser revertida, com reaplicação bem-sucedida após retirar o trigger. Alterações editoriais posteriores devem impedir tanto nova aplicação quanto rollback sem sobrescrever nada.

Contas, sessões, tokens e contatos devem permanecer vazios no ensaio. O seed real cria 117 logs de auditoria próprios; esses logs são preservados, sem importar os logs locais. O recibo técnico é uma linha adicional em `site_settings`, fora da contagem CMS. Rollback mantém arquivos finais de mídia para evitar remoção de arquivos potencialmente referenciados após confirmação de commit incerta.

Resultado final: **17 verificações de integração aprovadas**, além dos **19 testes offline aprovados** no pacote revisado. Evidência da execução concluída: `C:\Portifolio - Carlos Andre\.private\portfolio-editorial-stage-7d3efed5da\results.json`. Execuções interrompidas anteriores registram somente verificações alcançadas e não representam aprovação completa. Ao final, a listagem Docker confirmou ausência de containers, volumes e redes de staging; os containers locais originais continuaram ativos, sem reinício.

Este ensaio não valida a configuração atual da VPS, seu nome real de banco, espaço, permissões ou imagem instalada. Esses itens precisam ser conferidos posteriormente, com autorização.

## Transferência manual pelo Windows — não executada

Executar no PowerShell. O primeiro SSH cria somente o diretório privado do portfólio. Não desabilitar a checagem da chave do host; conferir sua identidade por canal confiável caso o SSH solicite.

```powershell
$portfolioArchive = 'C:\Portifolio - Carlos Andre\.private\editorial-transfer-20261021T042605Z.tar.gz'
$portfolioExpected = '60812da2f38caa50b9a52fb04b07ab4a7689f78fde5538713b82fe848acd69c3'
if ((Get-FileHash -LiteralPath $portfolioArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $portfolioExpected) { throw 'SHA-256 divergente: interromper' }
ssh -p 22 root@187.77.248.237 'umask 077; install -d -m 0700 /opt/carlosandre-portfolio/.private /opt/carlosandre-portfolio/.private/editorial-migration /opt/carlosandre-portfolio/.private/editorial-migration/incoming'
if ($LASTEXITCODE -ne 0) { throw 'SSH falhou: interromper sem transferir' }
scp -P 22 $portfolioArchive "$portfolioArchive.sha256" root@187.77.248.237:/opt/carlosandre-portfolio/.private/editorial-migration/incoming/
if ($LASTEXITCODE -ne 0) { throw 'SCP falhou: interromper e conferir o destino' }
ssh -p 22 root@187.77.248.237 'chmod 600 /opt/carlosandre-portfolio/.private/editorial-migration/incoming/editorial-transfer-20261021T042605Z.tar.gz /opt/carlosandre-portfolio/.private/editorial-migration/incoming/editorial-transfer-20261021T042605Z.tar.gz.sha256'
```

Transferir somente esses dois arquivos. Não transferir dump integral, `.env`, chaves, contas, sessões, contatos, diretório de auditoria ou pacote antigo. Se a autenticação falhar, interromper; não enviar senhas nem chaves privadas.

## Conferência no destino — manual, sem importação

Após entrar via `ssh -p 22 root@187.77.248.237`, executar em Bash:

```bash
set -euo pipefail
umask 077
cd /opt/carlosandre-portfolio/.private/editorial-migration/incoming
printf '%s  %s\n' '60812da2f38caa50b9a52fb04b07ab4a7689f78fde5538713b82fe848acd69c3' 'editorial-transfer-20261021T042605Z.tar.gz' | sha256sum -c -
sha256sum -c editorial-transfer-20261021T042605Z.tar.gz.sha256
# Não sobrepor uma extração existente.
test ! -e editorial-transfer-20261021T042605Z
tar --no-same-owner -xzf editorial-transfer-20261021T042605Z.tar.gz
cd editorial-transfer-20261021T042605Z
sha256sum -c SHA256SUMS
```

O primeiro comando compara contra o hash deste relatório, além do checksum que acompanhou o arquivo. A conferência completa do manifesto e integridade lógica é feita pelo modo `verify`, com a imagem backend, na etapa futura autorizada.

## Importação futura — exige nova autorização; não executada

Pré-condições: PostgreSQL exclusivo do portfólio disponível, versão 16, schema Alembic 0003, imagem backend compatível, volume de uploads com hard links e permissão UID 10001, backup verificável do **destino** e dos uploads. Confirmar o nome real do banco; `portfolio_prod` abaixo é o exemplo do repositório. Interromper escritores apenas do portfólio numa janela aprovada. Estes comandos não criam infraestrutura nem iniciam dependências.

```bash
set -euo pipefail
umask 077
portfolio_package=/opt/carlosandre-portfolio/.private/editorial-migration/incoming/editorial-transfer-20261021T042605Z
portfolio_review=/opt/carlosandre-portfolio/.private/editorial-migration/review/28d148d5810b0d3350e10ac468f933003335c98b139289c80ca42b55b9686050
# Proprietário alterado SOMENTE no novo pacote extraído.
chown -R 10001:10001 "$portfolio_package"
install -d -m 0700 /opt/carlosandre-portfolio/.private/editorial-migration/review
install -d -m 0700 -o 10001 -g 10001 "$portfolio_review"
cd /opt/carlosandre-portfolio
portfolio_compose=(docker compose -p carlosandre-portfolio-prod --env-file .env.production -f docker-compose.prod.yml)
portfolio_db=portfolio_prod # substituir pelo nome confirmado, sem expor credenciais
"${portfolio_compose[@]}" run --rm --no-deps --user 10001:10001 -v "$portfolio_package:/migration:ro" backend python /migration/tools/editorial_transfer.py verify /migration
"${portfolio_compose[@]}" run --rm --no-deps --user 10001:10001 -v "$portfolio_package:/migration:ro" -v "$portfolio_review:/review" backend python /migration/tools/editorial_transfer.py plan /migration --expected-database "$portfolio_db" --output /review/plan.json
```

**Parar e revisar o plano privado antes de escrever.** Conflitos impedem continuar. Qualquer alteração no destino entre planejamento e aplicação invalida o plano; gerar outro plano em arquivo novo, sem editar operações manualmente. Manter o plano original para rollback.

Somente após autorização de importação real:

```bash
"${portfolio_compose[@]}" run --rm --no-deps --user 10001:10001 -v "$portfolio_package:/migration:ro" -v "$portfolio_review:/review:ro" backend python /migration/tools/editorial_transfer.py apply /migration --expected-database "$portfolio_db" --approved-plan /review/plan.json --confirm-production-write
```

Validar os 122 conteúdos incorporados, estados, revisões, relacionamentos, hashes e leitura pelo painel/páginas. O destino pode conter conteúdos independentes adicionais, que devem ser preservados. Repetir o mesmo pacote sem mudanças posteriores não grava novamente; alterações posteriores provocam recusa segura.

## Rollback futuro

Falhas SQL revertem a transação inteira. Arquivos finais permanecem; não apagá-los em resposta a falha ou timeout. Conferir o recibo em caso de commit incerto. Com importação confirmada e nenhuma edição posterior, usar o mesmo pacote e plano, somente após autorizar a reversão:

```bash
"${portfolio_compose[@]}" run --rm --no-deps --user 10001:10001 -v "$portfolio_package:/migration:ro" -v "$portfolio_review:/review:ro" backend python /migration/tools/editorial_transfer.py rollback /migration --expected-database "$portfolio_db" --approved-plan /review/plan.json --confirm-production-write --confirm-rollback
```

A reversão compara o hash anterior, conserva o recibo como `rolled_back` e mantém as mídias. Edições posteriores bloqueiam rollback automático; nesse caso, reconciliar seletivamente com o backup do destino, preservando as novas alterações. Nunca restaurar o dump local integral sobre produção. Não usar `TRUNCATE`, remoção de volumes ou downgrade para esse procedimento.
