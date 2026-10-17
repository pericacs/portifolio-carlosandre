# Produção — VPS Hostinger compartilhada

Estado em 17/10/2026: arquitetura Docker recuperada para homologação na VPS Hostinger existente. Nenhum deploy, DNS, certificado ou envio Gmail foi executado. O Compose local continua independente. Não use `compose.yaml` para produção.

## Arquitetura e pré-requisitos

Linux com Docker Engine, plugin Compose v2 recente (`up --wait`), Bash, flock, curl, openssl, git e espaço para imagens, banco e backups. Clone em `/opt/carlosandre-portfolio`. Todos os comandos abaixo partem desse diretório. O projeto compartilha a VPS com SmartFamily (`/opt/smartfamily`), que não deve ser alterado. Não copie `.env`, uploads ou banco do computador local.

`docker-compose.prod.yml` fixa o projeto `carlosandre-portfolio-prod`. Os volumes `carlosandre-portfolio-prod_postgres_data` e `carlosandre-portfolio-prod_media_data` sobrevivem à recriação dos containers. Nunca execute `down -v`. Somente o Nginx do projeto publica `127.0.0.1:8088:80`. O Nginx já existente no host atende 80/443 e encaminha este domínio para a porta local 8088, sem modificar os virtual hosts do SmartFamily. A rede `private` é interna; API e worker também têm saída pela rede `egress` para SMTP. PostgreSQL não participa de `egress`. Não existem bind mounts de código nem portas públicas da API ou do banco.

O frontend reutiliza o Dockerfile multi-stage existente, com standalone e usuário node. O backend tem Dockerfile de produção separado, com wheels e UID 10001 sem root. Os containers persistentes usam `unless-stopped`. Health checks identificam falhas; Docker Compose **não reinicia um processo apenas por ficar unhealthy**. Monitore esse estado e investigue ciclos do worker; o heartbeat exige ciclo completo nos últimos 90 segundos. A queda do processo provoca reinício automático.

## Configuração na VPS

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

Edite o arquivo diretamente na VPS: senha PostgreSQL aleatória, exclusiva, com pelo menos 32 caracteres; Gmail e destinatário reais; `RELEASE_TAG` único por revisão (por exemplo SHA do commit). Nunca reutilize uma tag ao atualizar: rollback depende das imagens anteriores. Guarde esse arquivo em cofre separado e não em Git. Não imprima `docker compose config` em logs públicos; ele expande segredos. Use `config --quiet`.

Para Gmail: habilite verificação em duas etapas e crie uma senha de app quando a conta permitir. Use `smtp.gmail.com:587`, STARTTLS ativo, usuário Gmail completo e remetente autorizado pela mesma conta. `SMTP_PASSWORD` recebe a senha de app, nunca a senha normal. Políticas Workspace podem impedir senhas de app; valide com o administrador da conta. Sem SMTP completo, a fila fica pausada e preservada. Autenticação e entrega real precisam de teste na VPS; a aceitação SMTP não garante chegada à caixa de entrada.

## HTTPS e Cloudflare

Crie registros DNS A (e AAAA somente com IPv6 configurado) para `carlosandre.tech`, com proxy Cloudflare habilitado. Configure SSL/TLS como **Full (strict)**. Emita um certificado Cloudflare Origin CA para `carlosandre.tech` ou instale certificado de CA pública. O TLS termina no Nginx existente do host. O arquivo `infra/nginx/host-portfolio.conf.example` é apenas um modelo de virtual host dedicado; revise o certificado e seus caminhos antes de instalar. O modelo usa `/etc/letsencrypt/live/carlosandre.tech/`. Para Origin CA, ajuste apenas esse virtual host para os caminhos correspondentes e proteja a chave. Esses arquivos nunca entram no repositório; não monte certificados no container HTTP. Origin CA só é confiável para acesso através da Cloudflare.

Habilite Always Use HTTPS. Configure regra de cache **Bypass** para `/admin*` e `/api/*`; não aplique Cache Everything ao HTML dinâmico ou a respostas autenticadas. A aplicação usa origem canônica exata, cookies Secure e SameSite Strict, sessão HttpOnly, tokens de sessão armazenados como hash, CSRF vinculado à sessão e expiração. CORS de produção aceita somente a origem canônica. Swagger fica desabilitado. O Nginx sobrescreve cabeçalhos encaminhados e não confia em `CF-Connecting-IP` sem uma lista de proxies confiáveis; o rate limit no Nginx agrega tráfego por IP da borda Cloudflare. O rate limit de login da aplicação continua ativo.

Cloudflare fica somente na camada DNS, HTTPS e WAF deste domínio; não são necessários Workers, D1 ou R2. Na VPS compartilhada, não substitua regras globais de firewall nem altere TLS, rede ou virtual hosts do SmartFamily. Planeje proteção de origin e rate limiting especificamente para `carlosandre.tech`, considerando os demais sites antes de qualquer regra global. A porta 8088 fica vinculada a loopback; PostgreSQL e FastAPI não publicam portas. Preserve saída SMTP 587. Certificados e renovação pertencem ao Nginx do host. Em implantação futura, valide `nginx -t` e só então recarregue o Nginx existente, mediante autorização; não reinicie serviços indiscriminadamente.

Referências: [Cloudflare Origin CA](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/), [Full strict](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/), [ordem e health checks Compose](https://docs.docker.com/compose/how-tos/startup-order/).

## Primeiro deploy (somente na próxima etapa)

Antes de implantar, o script `preflight.sh` verifica o diretório, listeners do host e portas publicadas por containers. Ele aborta se 8088 estiver ocupada por outro serviço; nunca para o ocupante. A disponibilidade anterior informada pelo proprietário não substitui esta verificação. Nenhum acesso SSH à VPS foi realizado nesta recuperação.

```bash
bash scripts/production/preflight.sh
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

`bash scripts/production/backup.sh` pausa os escritores e Nginx, gera dump custom PostgreSQL, arquivo tar de uploads, revisão do checkout, referências configuradas de imagens, imagens efetivamente utilizadas (`running-images.txt`) e checksums em `backups/UTC-random/`, com permissões restritas, e reinicia os serviços. Para backup anterior a atualização, a revisão do checkout pode já ser a nova; use o registro de releases e as imagens efetivas para escolher a revisão de recuperação. Os backups contêm dados pessoais; copie-os criptografados para armazenamento externo com acesso restrito. Defina retenção e teste recuperação regularmente. Exemplo de cron na VPS: `0 3 * * * cd /opt/carlosandre-portfolio && /usr/bin/bash scripts/production/backup.sh >> /var/log/carlosandre-backup.log 2>&1`. Configure logrotate para esse arquivo; não foi instalado nesta etapa. Meta inicial sugerida: backup diário (RPO até 24h); RTO precisa ser medido na VPS.

Teste sem tocar produção:

```bash
bash scripts/production/restore-drill.sh backups/PASTA
```

O ensaio cria banco e volumes descartáveis, valida checksums, restaura banco e uploads, mostra revisão e quantidade de arquivos e remove apenas seus próprios recursos. Compare também contagens de negócio e abra os arquivos em uma homologação antes de aceitar a recuperação.

Restauração real exige janela de manutenção e backup de segurança atual. Use apenas backups próprios confiáveis, nunca arquivos tar de terceiros. Selecione checkout/imagens compatíveis com `revision.txt` e o histórico de releases. Execute:

```bash
bash scripts/production/restore.sh backups/PASTA --confirm-replace-production
bash scripts/production/preflight.sh
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --no-build --wait backend frontend worker nginx
```

O restore para os escritores, restaura o dump em transação única e substitui uploads. Não reinicia serviços automaticamente: falha parcial de mídia exige repetir a recuperação antes de abrir tráfego. Preserve o backup até verificar arquivos, relacionamentos, login e contagens. Não há migração automática no comando final de recuperação.

## Verificação repetível

```bash
docker build -f backend/Dockerfile.prod -t carlosandre-production-check-backend backend
docker build -t carlosandre-production-check-frontend frontend
python scripts/verify-production.py --visual
```

O verificador usa senha sintética, rede e volumes com identificadores aleatórios, sem ler `.env` ou alterar containers locais existentes. Sem `--visual`, não lê banco local nem publica portas. Com `--visual`, lê um dump consistente e os uploads da instância local exclusivamente para uma cópia descartável, publica uma porta aleatória em loopback e compara com `http://localhost:8080`. As mensagens reais permanecem somente nas bases locais; nada é enviado para a nuvem. Exige Python 3 e Docker; `--visual` exige também Node, Playwright/Chromium e sharp (use `PLAYWRIGHT_MODULE` e `SHARP_MODULE` para apontar instalações existentes), além da instância de referência local já rodando. executa suíte backend, migrações, reinicialização do banco, persistência de mídia, restauração lógica, validações de produção, início do frontend e API, TLS no proxy de host simulado, encaminhamento ao Nginx HTTP e sintaxe dos scripts Bash. Certificado de teste descartável não é certificado de produção. A limpeza remove apenas recursos do ensaio. Os testes de e-mail usam mocks e não enviam mensagens.

Antes da liberação: validar DNS, cadeia TLS e firewall externamente; conferir health checks; testar upload após recriação; executar backup/restore-drill com dados de homologação; testar SMTP real, recuperação e contato; configurar alertas de disco, backup, certificados, unhealthy e filas. Logs Docker giram em 5 arquivos de 10 MB por serviço. Revise periodicamente imagens base e dependências; mantenha imagens anteriores para rollback e não execute prune indiscriminado.

## Recursos e proteção da instalação compartilhada

Os limites de memória/CPU de runtime estão explícitos no Compose: banco 512 MB/0,75 CPU, frontend 512 MB/0,75 CPU, API 384 MB/0,50 CPU, worker 256 MB/0,25 CPU e Nginx 64 MB/0,25 CPU; a migração usa 384 MB/0,50 CPU temporariamente. Isso limita este projeto, mas não reserva capacidade. Antes de implantar, conferir capacidade disponível sem modificar SmartFamily; builds também consomem recursos e devem ocorrer em janela planejada ou em outra máquina. Não executar prune global, down global ou comandos em `/opt/smartfamily`. O nome novo de projeto gera volumes novos: qualquer transporte de dados será um procedimento separado, com backup e validação, nunca reaproveitando volumes de outros projetos.
