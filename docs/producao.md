# Produção — VPS exclusiva

Estado em 16/10/2026: infraestrutura preparada para homologação na VPS. Nenhum deploy, DNS, certificado ou envio Gmail foi executado. O Compose local continua independente. Não use `compose.yaml` para produção.

## Arquitetura e pré-requisitos

Linux com Docker Engine, plugin Compose v2 recente (`up --wait`), Bash, flock, curl, openssl, git e espaço para imagens, banco e backups. Clone em `/opt/carlosandre`. Todos os comandos abaixo partem desse diretório. A VPS deve ser exclusiva deste projeto. Não copie `.env`, uploads ou banco do computador local.

`docker-compose.prod.yml` fixa o projeto `carlosandre-production`. Os volumes `carlosandre-production_postgres_data` e `carlosandre-production_media_data` sobrevivem à recriação dos containers. Nunca execute `down -v`. Só o Nginx publica portas 80/443. A rede `private` é interna; API e worker também têm saída pela rede `egress` para SMTP. PostgreSQL não participa de `egress`. Não existem bind mounts de código nem portas públicas da API ou do banco.

O frontend reutiliza o Dockerfile multi-stage existente, com standalone e usuário node. O backend tem Dockerfile de produção separado, com wheels e UID 10001 sem root. Os containers persistentes usam `unless-stopped`. Health checks identificam falhas; Docker Compose **não reinicia um processo apenas por ficar unhealthy**. Monitore esse estado e investigue ciclos do worker; o heartbeat exige ciclo completo nos últimos 90 segundos. A queda do processo provoca reinício automático.

## Configuração na VPS

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

Edite o arquivo diretamente na VPS: senha PostgreSQL aleatória, exclusiva, com pelo menos 32 caracteres; Gmail e destinatário reais; `RELEASE_TAG` único por revisão (por exemplo SHA do commit); `TLS_DIR=/etc/carlosandre/tls`. Nunca reutilize uma tag ao atualizar: rollback depende das imagens anteriores. Guarde esse arquivo em cofre separado e não em Git. Não imprima `docker compose config` em logs públicos; ele expande segredos. Use `config --quiet`.

Para Gmail: habilite verificação em duas etapas e crie uma senha de app quando a conta permitir. Use `smtp.gmail.com:587`, STARTTLS ativo, usuário Gmail completo e remetente autorizado pela mesma conta. `SMTP_PASSWORD` recebe a senha de app, nunca a senha normal. Políticas Workspace podem impedir senhas de app; valide com o administrador da conta. Sem SMTP completo, a fila fica pausada e preservada. Autenticação e entrega real precisam de teste na VPS; a aceitação SMTP não garante chegada à caixa de entrada.

## HTTPS e Cloudflare

Crie registros DNS A (e AAAA somente com IPv6 configurado) para `carlosandre.tech`, com proxy Cloudflare habilitado. Configure SSL/TLS como **Full (strict)**. Emita um certificado Cloudflare Origin CA para `carlosandre.tech` ou instale certificado de CA pública. Na VPS, coloque a cadeia em `/etc/carlosandre/tls/fullchain.pem` e a chave em `privkey.pem`, com diretório 700 e chave 600, propriedade root. Esses arquivos nunca entram no repositório. O Nginx recusa iniciar sem certificado/chave válidos. Origin CA só é confiável para acesso através da Cloudflare.

Habilite Always Use HTTPS. Configure regra de cache **Bypass** para `/admin*` e `/api/*`; não aplique Cache Everything ao HTML dinâmico ou a respostas autenticadas. A aplicação usa origem canônica exata, cookies Secure e SameSite Strict, sessão HttpOnly, tokens de sessão armazenados como hash, CSRF vinculado à sessão e expiração. CORS de produção aceita somente a origem canônica. Swagger fica desabilitado. O Nginx sobrescreve cabeçalhos encaminhados e não confia em `CF-Connecting-IP` sem uma lista de proxies confiáveis; o rate limit no Nginx agrega tráfego por IP da borda Cloudflare. O rate limit de login da aplicação continua ativo.

No firewall do provedor e nas regras DOCKER-USER/nftables, permita 80/443 somente das faixas oficiais atuais da Cloudflare; permita SSH somente de IPs administrativos. Docker pode contornar regras simples de UFW: valide externamente portas IPv4 e IPv6. Mantenha as faixas Cloudflare atualizadas. Avalie Authenticated Origin Pulls como defesa adicional. Não restrinja saída SMTP 587. Renove o certificado antes da expiração e aplique `docker compose --env-file .env.production -f docker-compose.prod.yml exec nginx nginx -t` e `... exec nginx nginx -s reload` após substituí-lo.

Referências: [Cloudflare Origin CA](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/), [Full strict](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/), [ordem e health checks Compose](https://docs.docker.com/compose/how-tos/startup-order/).

## Primeiro deploy (somente na próxima etapa)

```bash
bash scripts/production/deploy.sh --first-install
docker compose --env-file .env.production -f docker-compose.prod.yml exec backend python -m app.cli create-admin
docker compose --env-file .env.production -f docker-compose.prod.yml exec backend python -m app.import_cms
```

O administrador é criado interativamente, sem senha padrão. A importação é explícita, usa apenas conteúdo já versionado e não publica rascunhos. Não importa banco ou credenciais locais. Teste login, logout, recuperação, upload e contato com dados de homologação antes de liberar acesso.

## Atualização e rollback

Antes de mudar o checkout, registre SHA, tag e `alembic current`. Faça fetch e checkout de uma revisão revisada, configure uma nova `RELEASE_TAG` no arquivo da VPS e execute `bash scripts/production/update.sh`. O script constrói primeiro, realiza backup consistente, interrompe escritores, migra e sobe os serviços com espera por saúde. Falha de migração mantém escritores parados; não há continuação silenciosa. Os scripts usam lock exclusivo e não executam git pull automaticamente.

Alembic usa transações PostgreSQL, advisory lock transacional, espera máxima de lock de 10s e timeout de statement de 5min. Toda migração futura exige revisão e teste com volume semelhante ao real. Mudanças destrutivas devem seguir expansão, transição e remoção em releases separados. O lock só protege clientes que usam esse mesmo fluxo; não execute DDL paralelo manual. Backup é obrigatório antes de migrar.

Para rollback **compatível com o schema atual**, execute `bash scripts/production/rollback.sh TAG_ANTERIOR`, depois registre essa tag no `.env.production` e alinhe o checkout à revisão anterior. O script reutiliza imagens locais e não faz build nem downgrade. Se o schema for incompatível, mantenha escritores parados, escolha checkout/imagens do backup e siga a restauração abaixo. Retorne somente após verificar saúde e fluxos administrativos. Não execute `alembic downgrade` automaticamente; restauração perde alterações posteriores ao backup.

## Backup e restauração

`bash scripts/production/backup.sh` pausa os escritores e Nginx, gera dump custom PostgreSQL, arquivo tar de uploads, revisão do checkout, referências configuradas de imagens, imagens efetivamente utilizadas (`running-images.txt`) e checksums em `backups/UTC-random/`, com permissões restritas, e reinicia os serviços. Para backup anterior a atualização, a revisão do checkout pode já ser a nova; use o registro de releases e as imagens efetivas para escolher a revisão de recuperação. Os backups contêm dados pessoais; copie-os criptografados para armazenamento externo com acesso restrito. Defina retenção e teste recuperação regularmente. Exemplo de cron na VPS: `0 3 * * * cd /opt/carlosandre && /usr/bin/bash scripts/production/backup.sh >> /var/log/carlosandre-backup.log 2>&1`. Configure logrotate para esse arquivo; não foi instalado nesta etapa. Meta inicial sugerida: backup diário (RPO até 24h); RTO precisa ser medido na VPS.

Teste sem tocar produção:

```bash
bash scripts/production/restore-drill.sh backups/PASTA
```

O ensaio cria banco e volumes descartáveis, valida checksums, restaura banco e uploads, mostra revisão e quantidade de arquivos e remove apenas seus próprios recursos. Compare também contagens de negócio e abra os arquivos em uma homologação antes de aceitar a recuperação.

Restauração real exige janela de manutenção e backup de segurança atual. Use apenas backups próprios confiáveis, nunca arquivos tar de terceiros. Selecione checkout/imagens compatíveis com `revision.txt` e o histórico de releases. Execute:

```bash
bash scripts/production/restore.sh backups/PASTA --confirm-replace-production
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --no-build --wait backend frontend worker nginx
```

O restore para os escritores, restaura o dump em transação única e substitui uploads. Não reinicia serviços automaticamente: falha parcial de mídia exige repetir a recuperação antes de abrir tráfego. Preserve o backup até verificar arquivos, relacionamentos, login e contagens. Não há migração automática no comando final de recuperação.

## Verificação repetível

```bash
docker build -f backend/Dockerfile.prod -t carlosandre-production-check-backend backend
docker build -t carlosandre-production-check-frontend frontend
python scripts/verify-production.py
```

O verificador usa senha sintética, rede e volumes com identificadores aleatórios, sem ler `.env`, publicar portas ou acessar banco local. Exige Python 3 e Docker; executa suíte backend, migrações, reinicialização do banco, persistência de mídia, restauração lógica, validações de produção, início do frontend e API, sintaxe TLS Nginx e scripts Bash. Certificado de teste descartável não é certificado de produção. A limpeza remove apenas recursos do ensaio. Os testes de e-mail usam mocks e não enviam mensagens.

Antes da liberação: validar DNS, cadeia TLS e firewall externamente; conferir health checks; testar upload após recriação; executar backup/restore-drill com dados de homologação; testar SMTP real, recuperação e contato; configurar alertas de disco, backup, certificados, unhealthy e filas. Logs Docker giram em 5 arquivos de 10 MB por serviço. Revise periodicamente imagens base e dependências; mantenha imagens anteriores para rollback e não execute prune indiscriminado.
