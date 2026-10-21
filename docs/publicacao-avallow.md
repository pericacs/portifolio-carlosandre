# Publicação manual do AVALLOW

Preparação local em 21/10/2026. **Nenhum comando deste procedimento foi executado na VPS.**

## Versão e dependências

- Implementação original: `codex/avallow-card-fix`, `7c5ed388c8ec272dab0d74b872ce55b91a0ac7b8`.
- Versão mínima: `codex/avallow-production`, correção reaplicada em `da2a648bcf0b65837d9904688cba50f87b555803` sobre Docker `258cef8`. A branch não contém o commit DOCX `7ee066d`. Commits posteriores nesta branch documentam a publicação e permitem selecionar a imagem backend do ensaio.
- Depende de **código frontend e dados CMS**. Código fornece imagem, enquadramento, apresentação inicial e leitura do status; os cinco campos ficam no PostgreSQL após salvar/publicar pelo CMS.
- Não exige troca de backend, worker, PostgreSQL, Nginx, schema, DNS ou Cloudflare. A imagem é um asset estático versionado, não um upload a transferir entre volumes.
- Nome AVALLOW; status **Em desenvolvimento**; descrição e tags em `frontend/src/data/avallow.json`. A faixa é a do Beloria. ID, slug `onstar-scd`, source key e histórico do OnStar são preservados.
- SmartFamily, Beloria e Orquestrador IA não foram editados. A confirmação visual é feita nas duas larguras com comparação da página inteira fora do AVALLOW, além de HTML, dimensões e versões CMS dos demais projetos.

## Testes repetidos nesta preparação

- Build Docker Next.js e TypeScript da branch mínima: aprovados.
- Build Docker do backend da base Docker, sem dependências/rotas DOCX: aprovado, para ensaio de compatibilidade; não implica atualizar esse serviço na VPS.
- Ensaio PostgreSQL descartável e Playwright: aprovado. Salvamento, publicação, persistência dos cinco campos, idempotência e histórico OnStar preservados.
- Capturas e comparação integral antes/depois em 1440 e 390 px: zero pixels alterados fora do AVALLOW. Os outros três cards mantiveram HTML, dimensões e versões CMS.
- Evidências locais privadas: `.private/avallow-production/.private/portfolio-avallow-1215f7bde1/` a partir do workspace principal, com capturas `after-projects-1440.png`, `after-projects-390.png` e `report.json`.
- Nenhum dado original local foi alterado nesta preparação; banco, redes e containers do ensaio são descartáveis.

Reprodução a partir desta branch (Node com Playwright/Sharp disponíveis, ou variáveis `PLAYWRIGHT_MODULE`/`SHARP_MODULE`):

```powershell
docker build -t carlosandre-avallow-check-frontend frontend
docker build -f backend/Dockerfile.prod -t carlosandre-avallow-check-backend backend
$env:AVALLOW_BACKEND_IMAGE='carlosandre-avallow-check-backend'
python scripts/verify-avallow.py
```

A imagem de referência visual anterior é `carlosandre-docx-check-frontend`, mantida localmente da homologação original. Ela é usada somente como referência de renderização da Home; não será enviada nem instalada em produção.

Produção não foi inspecionada nesta etapa: confirmar commit instalado, projeto Compose, versão do registro, saúde e porta 8088 antes de prosseguir. Se a produção tem commits próprios posteriores, **não voltar para esta branch descartando-os**: integrar o commit AVALLOW na linha de produção e repetir a validação.

## 1. Disponibilizar a branch, manualmente no Windows

Após revisão deste código/documento, na cópia local do repositório:

```powershell
git push origin codex/avallow-production:codex/avallow-production
```

O push não foi executado nesta preparação. Não enviar `.private`, backups, `.env`, banco ou pacotes editoriais.

## 2. Verificações e backup na VPS

Usar a mesma sessão Bash para os blocos seguintes. Nenhuma operação global de Docker é necessária.

```bash
set -Eeuo pipefail
cd /opt/carlosandre-portfolio
test "$(pwd -P)" = /opt/carlosandre-portfolio
test -z "$(git status --porcelain)" # se falhar, revisar alterações; não apagar
umask 077
exec 9>/tmp/carlosandre-portfolio-prod.lock
flock -n 9
dc() { docker compose -p carlosandre-portfolio-prod --env-file .env.production -f docker-compose.prod.yml "$@"; }
dc ps
bash scripts/production/preflight.sh
ANTES=$(git rev-parse HEAD)
git fetch origin codex/avallow-production
git merge-base --is-ancestor "$ANTES" origin/codex/avallow-production
# Se a ancestralidade falhar, interromper e integrar na linha instalada.
BACKUP="backups/avallow-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 -p "$BACKUP"
printf '%s\n' "$ANTES" > "$BACKUP/commit-before.txt"
WEB=$(dc ps -q frontend)
test -n "$WEB"
OLD_ID=$(docker inspect --format '{{.Image}}' "$WEB")
OLD_TAG="carlosandre-portfolio-frontend:before-avallow-$(date -u +%Y%m%dT%H%M%SZ)"
docker tag "$OLD_ID" "$OLD_TAG"
printf '%s\n' "$OLD_TAG" > "$BACKUP/frontend-before.txt"
dc exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$BACKUP/database.dump"
dc exec -T db pg_restore --list < "$BACKUP/database.dump" > "$BACKUP/database.list"
dc exec -T backend python -c 'import json,sqlalchemy as s; from app.db import get_engine; from app import models as m; c=get_engine().connect(); r=c.execute(s.select(m.cms_entries).where(m.cms_entries.c.module=="projetos",m.cms_entries.c.source_key=="initial:projetos:onstar-scd")).mappings().one(); print(json.dumps(dict(r),default=str)); c.close()' > "$BACKUP/avallow-before.json"
(cd "$BACKUP" && sha256sum database.dump avallow-before.json > SHA256SUMS && sha256sum -c SHA256SUMS)
```

O dump é somente leitura, consistente no PostgreSQL, sem pausar serviços. Contém dados privados: manter na VPS com acesso restrito, fora do Git. Nenhum arquivo de mídia será alterado nesta publicação; o asset novo pertence à imagem frontend. O teste de restauração de um backup real deve ocorrer em banco descartável antes de uma recuperação; `pg_restore --list` é apenas a conferência estrutural, não prova de restauração completa.

## 3. Atualizar exclusivamente o frontend do portfólio

```bash
git switch --detach origin/codex/avallow-production
git rev-parse HEAD                 # conferir com o commit aprovado na entrega
sha256sum frontend/public/images/avallow-fintech.png
# Esperado: a1436552052ea70e34bd4f4da68d0c803eca93473fdae0d5c9077807e046b55a
printf '%s  %s\n' a1436552052ea70e34bd4f4da68d0c803eca93473fdae0d5c9077807e046b55a frontend/public/images/avallow-fintech.png | sha256sum -c -
NEW_TAG=carlosandre-portfolio-frontend:avallow-da2a648
mkdir -m 700 -p .private
OVERRIDE=.private/compose.avallow.yml
printf 'services:\n  frontend:\n    image: %s\n' "$NEW_TAG" > "$OVERRIDE"
av() { docker compose -p carlosandre-portfolio-prod --env-file .env.production -f docker-compose.prod.yml -f "$OVERRIDE" "$@"; }
av config --quiet
av build frontend
# A troca ocorre só depois de o build terminar com sucesso.
av up -d --no-deps --no-build --wait --wait-timeout 180 frontend
curl --fail --retry 8 --retry-delay 3 --retry-all-errors -H 'Host: carlosandre.tech' http://127.0.0.1:8088/ -o /dev/null
curl --fail -H 'Host: carlosandre.tech' http://127.0.0.1:8088/images/avallow-fintech.png -o "$BACKUP/image-served.png"
sha256sum "$BACKUP/image-served.png"
printf '%s  %s\n' a1436552052ea70e34bd4f4da68d0c803eca93473fdae0d5c9077807e046b55a "$BACKUP/image-served.png" | sha256sum -c -
```

Há uma breve troca do container frontend do portfólio. `--no-deps` impede a inicialização/recriação de outros serviços, incluindo o serviço `migrate`. Não executar `update.sh`, `rollback.sh` geral, `compose up` sem especificar frontend, `down`, `prune` ou qualquer comando no diretório do SmartFamily para esta correção.

O override deve continuar sendo incluído nas operações futuras deste frontend, ou ser incorporado posteriormente à configuração de release adotada pela operação. Não alterar `RELEASE_TAG` global para esta troca, pois ele também controla backend/worker.

## 4. Salvar e publicar os dados CMS

Abrir o registro existente OnStar/AVALLOW no painel e conferir a versão e o histórico. Revisar também eventuais edições pendentes nesse registro: publicar leva o rascunho inteiro, não apenas os cinco campos. Se houver diferenças não aprovadas, parar para revisão.

Pode-se editar os cinco campos pelo painel, sem utilitário. Alternativamente, com Python 3 já disponível na VPS, o utilitário faz dry-run e depois salva **somente um rascunho**, com proteção por versão:

```bash
BACKEND=$(dc ps -q backend)
test -n "$BACKEND"
read -r -p 'Versão atual conferida no painel: ' VERSAO
python3 scripts/update-avallow.py --container "$BACKEND" --expected-version "$VERSAO"
# Conferir o plano antes da próxima linha:
python3 scripts/update-avallow.py --container "$BACKEND" --expected-version "$VERSAO" --apply
```

No painel: conferir imagem, descrição, tags e **Em desenvolvimento**, revisar a prévia e usar a ação normal **Publicar**. Não criar outro projeto nem trocar seu slug. O script não publica, não importa pacotes, não cria contas e não sobrescreve os outros projetos. Se o pacote editorial antigo ainda será importado, fazê-lo em outra etapa autorizada antes desta correção; esta publicação não executa o importador.

Conferir a Home por HTTPS em 1440 e 390 px, a ordem dos quatro cards, o status e a imagem. Confirmar que os demais cards e seções continuam iguais. `curl` em loopback confirma a origem; conferir também o navegador público. Não limpar todo o cache da zona Cloudflare: se existir HTML antigo em cache, invalidar apenas a Home após confirmar a origem.

```bash
dc ps
flock -u 9
```

## Rollback mínimo

Antes da publicação CMS, uma falha pode ser revertida somente trocando a imagem frontend. Na sessão que conserva `$BACKUP`:

```bash
OLD_TAG=$(cat "$BACKUP/frontend-before.txt")
docker image inspect "$OLD_TAG" >/dev/null
printf 'services:\n  frontend:\n    image: %s\n' "$OLD_TAG" > .private/compose.avallow.yml
docker compose -p carlosandre-portfolio-prod --env-file .env.production -f docker-compose.prod.yml -f .private/compose.avallow.yml up -d --no-deps --no-build --wait --wait-timeout 180 frontend
```

Após publicar no CMS, o rollback da imagem **não reverte os dados**. Pelo painel, restaurar/revisar a revisão anterior do registro e publicar novamente a apresentação aprovada anterior. Conferir com `avallow-before.json`: se havia `published_data`, ela é a referência pública anterior; a revisão anterior pode conter rascunhos que nunca foram publicados. Se o card vinha do baseline sem publicação CMS, reconstruir os campos da apresentação anterior aprovada, sem publicar alterações pendentes não revisadas. Não usar simplesmente “Despublicar”, pois isso pode ocultar o card vindo do baseline.

Manter as revisões novas para auditoria. Não importar `database.dump` sobre produção nem reverter tabelas inteiras como rollback desta correção. Uma recuperação integral de banco exige análise das alterações posteriores, autorização separada e ensaio em banco descartável. SmartFamily, backend, worker, volumes, Nginx e DNS permanecem fora do rollback.
