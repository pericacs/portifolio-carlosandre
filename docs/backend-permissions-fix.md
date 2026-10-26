# Permissões do backend de produção

Correção na branch `codex/avallow-production`, limitada ao backend Docker e à prova de regressão. Não houve acesso à VPS ou alteração de outro projeto.

O Dockerfile preservava modos do contexto. O teste reproduziu `PermissionError` como `appuser` usando arquivos root-owned `0600` e diretórios `0700`, mesmo com os arquivos registrados no Git como `100644`. As ACLs Windows das fontes verificadas permitem leitura/execução; não foi necessário alterá-las. Permissões restritivas em outro host não impedem mais a inicialização da imagem construída.

`backend/Dockerfile.prod` normaliza:

- Arquivos de `app`, Alembic, configuração Alembic e requirements: `0644`.
- Diretórios de código e `/app`: `0755`.
- Código continua pertencendo ao root e não pode ser modificado pelo usuário da aplicação.
- Uploads pertencem ao `appuser`, com `0750`.
- `USER appuser`, UID 10001, preservado. Nenhum `chmod 777` ou execução da aplicação como root.

`backend/.dockerignore` e `backend/Dockerfile.prod.dockerignore` foram alinhados. O arquivo específico prevalece no build de produção e agora também exclui `.private`, backups e bytecode abrangente. `.env*`, ambientes virtuais, caches, uploads, testes e `.git` permanecem fora do contexto normal de build.

Prova executada com `python scripts/verify-backend-permissions.py`:

1. Build da versão anterior com contexto Linux sintético restritivo: falha de leitura reproduzida.
2. Build da versão corrigida com o mesmo contexto: permissões e ownership conferidos arquivo a arquivo, imports da aplicação/DOCX aprovados como UID 10001; código sem escrita e uploads com escrita.
3. Builds de diagnóstico em contexto de diretório normal: canários fictícios excluídos tanto pelo ignore geral quanto pelo específico. Nenhum `.env`, upload, backup ou credencial local real foi lido pelo teste.
4. PostgreSQL exclusivo descartável; Alembic executado somente nele. Imagem de produção com comando Uvicorn real iniciou e retornou sucesso nos endpoints `/api/health/live` e `/api/health/ready`, schema `0003`.
5. Worker iniciou como o mesmo UID 10001 e gerou heartbeat.
6. Containers, rede, volume e imagens exclusivos do ensaio removidos ao terminar.

O script único de implantação entregue anteriormente deve ser atualizado para o novo commit que contém esta correção. Nenhum deploy foi executado nesta tarefa.
