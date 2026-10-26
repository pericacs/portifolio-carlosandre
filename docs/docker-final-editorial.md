# Docker final e importador editorial PostgreSQL — 21/10/2026

Branch de entrega: `codex/docker-recovery-hostinger`, baseada em `7eb4be7`. Nenhum acesso à VPS, deploy, migração remota, transferência de pacote ou alteração de SmartFamily foi executado. Cloudflare permanece somente como futura camada de DNS, HTTPS e proteção.

## Preservação da experiência Cloudflare

A experiência local foi registrada na branch `codex/cloudflare-recovery`, commit `39d187d`, antes da troca de branch. As demais branches e commits de segurança continuam existentes, incluindo `codex/safety-before-docker-recovery-20261017` / `40e1511`. Nenhum reset destrutivo, exclusão de histórico ou push forçado foi utilizado.

A branch Docker não recebeu APIs Workers, vinext, D1, R2, schema SQLite, autenticação scrypt ou adaptadores Cloudflare. Os arquivos públicos, fotografia, componentes, estilos, conteúdos, dependências frontend, Compose e Nginx são os mesmos de `7eb4be7`. Artefatos WebP gerados no experimento foram preservados no diretório privado fora de `frontend/public`, sem alterar os arquivos originais.

## Correções incorporadas

O módulo `backend/app/editorial_transfer.py` passa a integrar a branch Docker. Ele opera exclusivamente com SQLAlchemy/psycopg e PostgreSQL 16, schema Alembic **0003**. Não é o importador D1/R2.

1. **Seed intocado:** a construção da referência agora reproduz exatamente `app.import_cms`: valida os dados com `cms_schema.validate`, descarta campos de origem que o seed não persiste e conserva `_legacy`. Antes, nove experiências intocadas eram recusadas porque o comparador mantinha campos brutos extras.
2. **Quantidade de linhas afetadas:** INSERT, UPDATE e DELETE usam `RETURNING id` explícito e contam os IDs retornados. O driver psycopg pode informar `rowcount=-1` em operações com retorno implícito; o importador antigo recusava uma operação válida. A verificação continua exigindo exatamente uma linha.

O importador verifica o pacote sem conectar ao banco no modo `verify`; o modo `plan` usa transação somente de leitura e gera um plano privado; `apply` exige plano aprovado, banco explícito, configuração de produção e confirmação de escrita. O plano é recalculado após locks de tabelas e advisory lock. Divergências ou mudanças posteriores são recusadas. Não executa migrações de schema.

A escrita é transacional e inclui recibo em `site_settings`. Reaplicação sem mudanças não grava novamente. Rollback reverte somente as operações do plano, recusa alterações posteriores e conserva mídias finais, inclusive em falhas de confirmação de commit. Mídia com chave existente e SHA divergente bloqueia a operação; nenhum arquivo existente é substituído.

Também foram reforçados `backend/.dockerignore` e `frontend/.dockerignore`: uploads, backups, ambientes e artefatos locais Cloudflare ficam fora dos contextos de build. Nenhum serviço ou design foi alterado.

## Compatibilidade do pacote

```text
Arquivo: C:\Portifolio - Carlos Andre\.private\editorial-transfer-20261021T042605Z.tar.gz
SHA-256 do arquivo: 60812da2f38caa50b9a52fb04b07ab4a7689f78fde5538713b82fe848acd69c3
SHA-256 do importador: 5890d347619e70fc69425025738fb45a3f14cf15f1a3288af20eb2cfbf9077cc
```

A cópia versionada do importador e `tools/editorial_transfer.py` dentro do pacote possuem o mesmo hash. O pacote revisado não foi modificado ou regenerado nesta etapa. Não usar as versões anteriores `041601Z` ou `042519Z`, nem o importador JavaScript D1 da branch Cloudflare.

Confirmados: **122 conteúdos**, **118 rascunhos e 4 publicações**, **28 arquivos de mídia**, **138 revisões**, **74 vínculos de conteúdo**, **56 referências de mídia** e integridade referencial. Os 429 registros selecionados em 25 tabelas incluem essas relações e metadados; não confundir 429 linhas com 122 conteúdos CMS. Contas, sessões, credenciais e mensagens locais permanecem excluídas.

## Testes executados nesta retomada

| Verificação | Resultado |
|---|---|
| Build backend de produção | Aprovado |
| Build Next.js standalone, incluindo TypeScript | Aprovado |
| Suíte geral backend | 81 aprovados; 18 dependentes de pacote privado omitidos nesta execução |
| Suíte editorial dedicada com pacote read-only | 19/19 aprovados, incluindo os 18 omitidos acima |
| Ensaio PostgreSQL real com pacote exato | 17/17 verificações aprovadas |
| Alembic upgrade repetido, check e revisão 0003 | Aprovados em banco descartável |
| Persistência de banco após restart descartável e uploads entre containers | Aprovada |
| pg_dump/pg_restore em outro banco descartável | Aprovado |
| Backup/restauração de uploads em outro volume | Aprovado |
| Health, docs desativadas em produção, cookies Secure, CSRF | Aprovados |
| Isolamento Compose, nomes exclusivos, banco/backend sem portas públicas | Aprovado |
| Proxy Nginx externo simulado → Nginx interno → serviços, com TLS de teste | Aprovado |
| Heartbeat worker Gmail e sintaxe dos scripts Bash | Aprovados |

O ensaio editorial foi repetido em banco vazio e banco com seed real de 117 conteúdos. Conferiu igualdade integral das tabelas editoriais ao pacote, 28 hashes no volume Linux, estados, FKs, planejamento somente de leitura, repetição sem escrita e rollback ao hash anterior. Um terceiro banco testou falha SQL deliberada na gravação do recibo: a transação inteira foi revertida; nova tentativa passou. Edições posteriores bloquearam importação e rollback sem sobrescrita.

Os testes comuns não exigem distribuir o pacote privado: testes que precisam dele usam fixture opcional; quando `EDITORIAL_TEST_PACKAGE` é definido explicitamente e o pacote está inválido/ausente, a execução falha, sem omitir silenciosamente a validação. O teste editorial dedicado monta o pacote somente de leitura.

Há um aviso de depreciação de `httpx`/Starlette na suíte, sem falha. Não houve teste de entrega Gmail real nem homologação atual de recursos/porta na VPS. Não se refez comparação visual nesta retomada porque nenhum componente, dado público, estilo ou imagem foi alterado; a identidade desses arquivos com `7eb4be7` foi conferida pelo Git. O relatório visual anterior permanece preservado.

Evidência sanitizada versionada: `docs/docker-final-editorial-tests.json`. Logs integrais e recibos de staging ficam em `.private/`, fora do Git. Recursos descartáveis não utilizam redes, volumes ou bancos originais. O teste não iniciou o Compose de produção.

## Atualizar somente o código na VPS — comandos manuais futuros

Esses comandos **não foram executados**. Eles atualizam Git, sem build, migração, importação, reload ou restart. Execute somente quando decidir atualizar a cópia; preserve `.env.production`, mídias e bancos existentes.

```bash
set -euo pipefail
cd /opt/carlosandre-portfolio
test "$(pwd -P)" = /opt/carlosandre-portfolio
# Qualquer alteração ou arquivo não ignorado exige análise antes de continuar.
if test -n "$(git status --porcelain --untracked-files=normal)"; then
  echo 'Checkout possui alterações; interromper e preservar antes de atualizar.' >&2
  exit 1
fi
git fetch origin codex/docker-recovery-hostinger
if git show-ref --verify --quiet refs/heads/codex/docker-recovery-hostinger; then
  git switch codex/docker-recovery-hostinger
else
  git switch --create --track codex/docker-recovery-hostinger origin/codex/docker-recovery-hostinger
fi
git merge --ff-only origin/codex/docker-recovery-hostinger
git log -1 --format='%H %s'
git status --short
```

Comparar o hash exibido com o commit informado na entrega. Se o fast-forward for recusado ou houver divergência, interromper; não usar reset, clean, rebase automático, stash indiscriminado ou push forçado. A atualização de Git não muda os containers em execução. Nenhum comando acima menciona `/opt/smartfamily`.

Antes de qualquer implantação futura, rever disponibilidade de `127.0.0.1:8088` pelo `scripts/production/preflight.sh`, inventário dos serviços e backups exclusivos do portfólio. Essa disponibilidade **não foi consultada agora**. A transferência manual e o plano de importação PostgreSQL ficam para a próxima autorização; o procedimento detalhado está em `docs/staging-editorial-20261021.md`.
