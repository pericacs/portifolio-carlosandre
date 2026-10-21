# DOCX: correção de 413 e respostas HTML

## Evidência e limites

- Documento real: `Artigo_Split_do_Mal_Completo_Illustrado.docx`, **3.996.642 bytes**, aproximadamente **3,81 MiB**. SHA-256 `ba394da4286d552f1d68b74c96945e3efc9a92dc1eac158ff90ded6e70448487`.
- FastAPI já limita o arquivo a **8.388.608 bytes (8 MiB)**, por leitura limitada. Esse teto não foi aumentado. O frontend agora bloqueia arquivos acima dele antes de fazer upload.
- Nginx do container e template externo tinham limite geral `10m`, suficiente para esse documento. Foram adicionadas regras **somente para `/api/admin/docx/preview`**, com `client_max_body_size 9m` (**9.437.184 bytes**) para arquivo de 8 MiB + envelope multipart. Outras rotas/hosts não recebem aumento de limite.
- Ambos devolvem JSON 413 quando esse teto de transporte é excedido. O limite de arquivo continua sendo aplicado na API, mesmo abaixo do teto de transporte.
- A [documentação Cloudflare de 413](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-413/) informa limite de 100 MB no Free/Pro e permite limite menor configurado na zona. O padrão não justifica rejeitar 3,81 MiB. Conferir **Network → Maximum Upload Size** e regras específicas da zona; o limite efetivo precisa comportar pelo menos 9 MiB de requisição. Se já for suficiente, não aumentá-lo. Não desativar proxy, WAF, autenticação ou CSRF para contornar o erro.
- O header `Server: cloudflare` sozinho não identifica quem gerou o 413: uma resposta da origem pode passar pela Cloudflare. O SSH continua recusado (`Permission denied (publickey,password)`); portanto os limites **ativos** do Nginx externo e da zona não puderam ser confirmados. Duas sondagens sintéticas sem credenciais receberam 403/Cloudflare 1010, não permitindo localizar o 413. Nenhum DOCX privado foi enviado nessas sondagens.

## Correção

O cliente compartilhado trata 413 antes de tentar JSON e mostra limite/diagnóstico em português. Respostas HTML/texto, inclusive na obtenção de CSRF, não geram mais `Unexpected token '<'`. Respostas JSON malformadas também têm mensagem controlada. Login, CSRF e multipart automático do navegador foram preservados; HTML recebido nunca é exibido como conteúdo.

O snippet `infra/nginx/host-docx-upload.conf` deve ser incluído **apenas no bloco HTTPS exclusivo do portfólio**. Não substituir `nginx.conf` ou configurações de outros projetos. O template `host-portfolio.conf.example` referencia esse snippet; um template versionado não altera o vhost já instalado.

O probe de implantação passou a usar DOCX sintético de **8 MiB**, com dez seções e quatro imagens. Um teste minúsculo não detectava um proxy configurado com limite baixo. O probe não salva nem publica artigo e cancela sua área temporária.

## Testes locais

- 10 cenários do cliente API: sucesso, 413 HTML/JSON, HTML 502, JSON inválido, sessão expirada, erro não JSON no CSRF, manutenção do token/multipart, token ausente e 204.
- 27 testes DOCX aprovados com referência privada montada: upload real com dez seções/quatro imagens; DOCX válido com exatamente 8 MiB aceito; 8 MiB + 1 byte recusado com JSON 413 e sem nova área de staging.
- Suíte geral: 106 aprovados e 20 opcionais pulados por falta de fixtures privadas nessa suíte. O documento real é executado separadamente.
- Os dois Nginx testados por HTTP/HTTPS: 8 MiB + multipart chegam à autenticação (401 sem sessão); requisição maior que 9 MiB é recusada com JSON 413.
- Build/TypeScript e Playwright: erro HTML 413 com mensagem legível seguido de importação real, revisão, persistência de rascunho e publicação explícita exclusivamente em banco descartável; desktop/mobile e design preservados.
- Ensaio conjunto verifica também o probe HTTP de 8 MiB e rollback direcionado, sem alterar outros registros CMS.

## Atualização mínima na VPS — manual, não executada

Primeiro consultar os limites efetivos (somente leitura), identificando o arquivo do **vhost do portfólio**. Não copiar a saída completa do Nginx para locais públicos:

```bash
sudo nginx -T 2>/dev/null | grep -nE 'configuration file|server_name|client_max_body_size|location = /api/admin/docx/preview'
```

Atualizar o código, recusando apagar alterações/commits locais. Este procedimento muda somente frontend e Nginx do portfólio; backend, worker e banco não precisam de troca para esta correção:

```bash
set -Eeuo pipefail
cd /opt/carlosandre-portfolio
test "$(pwd -P)" = /opt/carlosandre-portfolio
test -z "$(git status --porcelain)"
ANTES=$(git rev-parse HEAD)
git fetch origin codex/avallow-production
git merge-base --is-ancestor "$ANTES" origin/codex/avallow-production
git switch --detach origin/codex/avallow-production
umask 077
mkdir -p .private
ARGS=(-p carlosandre-portfolio-prod --env-file .env.production -f docker-compose.prod.yml)
for file in .private/compose.avallow.yml .private/compose.portfolio-release.yml; do
  [[ ! -f "$file" ]] || ARGS+=(-f "$file")
done
dc() { docker compose "${ARGS[@]}" -f .private/compose.docx413.yml "$@"; }
OLD=$(docker compose "${ARGS[@]}" ps -q frontend)
ROLLBACK_TAG="carlosandre-portfolio-frontend:before-docx413-$(date -u +%Y%m%dT%H%M%SZ)"
docker tag "$(docker inspect -f '{{.Image}}' "$OLD")" "$ROLLBACK_TAG"
printf '%s\n' "$ROLLBACK_TAG" > .private/docx413-frontend-before.txt
printf 'services:\n  frontend:\n    image: carlosandre-portfolio-frontend:docx413-%s\n' "$(git rev-parse --short HEAD)" > .private/compose.docx413.yml
dc build frontend
dc up -d --no-deps --no-build --wait --wait-timeout 180 frontend
dc up -d --no-deps --force-recreate --wait --wait-timeout 90 nginx
```

A recriação se limita ao Nginx do projeto: o bind mount de arquivo pode continuar apontando para o inode antigo após checkout Git, portanto somente `nginx -s reload` dentro do container pode não carregar o arquivo novo. Manter o override frontend nas operações posteriores, ou incorporá-lo à próxima configuração de release.

Instalar o snippet externo e adicionar **uma única vez**, dentro do bloco HTTPS exclusivo `server_name carlosandre.tech`, a linha:

```nginx
include /etc/nginx/snippets/carlosandre-docx-upload.conf;
```

Os comandos são:

```bash
sudo install -d -m 755 /etc/nginx/snippets
sudo install -m 644 infra/nginx/host-docx-upload.conf /etc/nginx/snippets/carlosandre-docx-upload.conf
# Editar somente o vhost identificado, preservando uma cópia privada anterior.
# Se o bloco compartilhar hosts de outros projetos, separar/revisar antes; não aplicar globalmente.
sudo nginx -t && sudo systemctl reload nginx
```

O reload externo é gracioso, sem editar o vhost SmartFamily. Não substituir o arquivo real inteiro pelo template. Confirmar o limite da zona Cloudflare sem alterar DNS/WAF. Então repetir no navegador autenticado a importação real e conferir Preview/Network: 201 JSON, dez seções, quatro imagens. Não publicar o artigo apenas para testar. Se persistir 413, comparar o erro/log do vhost com a configuração efetiva da zona; não elevar o limite geral como tentativa.

## Reversão

Não houve mudança de schema nem de dados CMS nesta correção. Para voltar o frontend, usar a tag salva em `.private/docx413-frontend-before.txt` no override e recriar somente frontend com `--no-deps --no-build`. Restaurar somente as regras do vhost/snippet do portfólio a partir da cópia anterior, testar com `nginx -t` e recarregar. Não restaurar banco, apagar uploads ou alterar outros projetos.
