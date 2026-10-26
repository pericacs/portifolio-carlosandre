# Recuperação Docker — Hostinger compartilhada — 17/10/2026

## Estado e segurança

A recuperação foi autorizada pelo proprietário após o diagnóstico. Não foi executado deploy, acesso SSH, reinício de serviço existente, alteração de DNS ou operação no SmartFamily. Nenhuma migração foi aplicada no PostgreSQL local original. Não foram utilizados reset destrutivo, clean ou push forçado.

Base Docker: `374533a`. Estado da tentativa Cloudflare preservado integralmente no commit `40e1511`, branch `codex/safety-before-docker-recovery-20261017`. A recuperação está na branch `codex/docker-recovery-hostinger`. O histórico anterior continua acessível; a branch de segurança não é um release para implantação.

A exportação privada da tentativa anterior (33 tabelas e 28 arquivos) continua em `.private/`, ignorada pelo Git. Ela não foi importada para nuvem. Dados reais usados na comparação visual foram copiados por leitura para banco e volume locais descartáveis. Credenciais de teste e dados privados não fazem parte do commit.

## Arquivos restaurados exatamente de 374533a

- `frontend/package.json`: scripts Next.js e dependências anteriores; removidos vinext, Wrangler, Vite e dependências das APIs Workers.
- `frontend/pnpm-lock.yaml`: resolução original das dependências, sem atualização oportunista de versões.
- `frontend/next-env.d.ts`: referências Next.js, sem augmentations vinext.
- `frontend/src/lib/admin-server.ts`: consultas administrativas SSR diretamente ao FastAPI, usando a sessão original.
- `frontend/src/lib/public-content.ts`: leitura pública diretamente do FastAPI e preservação integral da composição dos dados aprovados.

## Arquivos da tentativa retirados da aplicação ativa

Todos permanecem no commit de segurança:

- `frontend/.dev.vars.example`, `frontend/.gitignore`, `frontend/pnpm-workspace.yaml`, `frontend/vite.config.ts`, `frontend/wrangler.jsonc`.
- `frontend/src/lib/runtime-api.ts`.
- `frontend/cloudflare/api.ts`, `auth.ts`, `cms.ts`, `contact.ts`, `core.ts`, `media.ts`, `modules.d.ts`, `runtime-api.ts`, `schema.json`, `types.ts`, `validation.ts`, `worker.ts`.
- `frontend/cloudflare/migrations/0001_portfolio.sql` e `0002_atomic_writes.sql`.
- `scripts/cloudflare/schema.py`.

Não há migrações D1, autenticação Workers, objetos R2 ou APIs alternativas no caminho ativo. Autenticação, validação, sanitização, sessões, CSRF, CORS, revisão editorial, histórico, agendamentos e fila Gmail voltam integralmente às implementações FastAPI já existentes.

## Mantidos e preservados

Foram comparados com `374533a` e permanecem sem alterações: `frontend/src/app/`, `frontend/src/components/`, `frontend/src/data/`, `frontend/public/`, os Dockerfiles originais, `frontend/next.config.ts`, a API FastAPI, modelos e migrações PostgreSQL, autenticação Argon2id, worker Gmail, testes backend, `compose.yaml` e `compose.dev.yaml`. Isso inclui fotografia profissional, currículo, imagens, projetos, experiências, skills, cases, artigos, vídeos e painel visual.

Também foram mantidas as melhorias de produção já presentes na base: builds otimizados, usuário sem root, health checks, rotação de logs, volume de mídia, persistência PostgreSQL, proteção administrativa, backup/restore e locks/timeouts Alembic. Não havia nova funcionalidade de produto concluída durante a tentativa Workers além da infraestrutura experimental retirada.

O exportador somente de leitura foi preservado como utilitário opcional: `backend/app/export_cloudflare.py` foi renomeado para `backend/app/export_snapshot.py`, com documentação genérica. Ele gera uma cópia privada para auditoria e verifica hashes; não altera tabelas, não substitui `pg_dump` nem transmite dados. As regras de proteção para `.private/`, arquivos de ambiente e artefatos ignorados continuam no `.gitignore`. Artefatos locais ignorados da tentativa não participam das imagens Docker.

## Arquivos adaptados ou adicionados para hospedagem compartilhada

| Arquivo | Alteração |
|---|---|
| `docker-compose.prod.yml` | Projeto `carlosandre-portfolio-prod`, imagens `carlosandre-portfolio-*`, apenas `127.0.0.1:8088:80`, recursos exclusivos e limites de CPU/memória; retirado mount TLS |
| `.env.production.example` | Retirada de `TLS_DIR`; demais configurações continuam sem credenciais reais |
| `infra/nginx/production.conf` | Nginx interno HTTP, proxy para Next.js/FastAPI; HTTPS externo indicado ao upstream |
| `infra/nginx/host-portfolio.conf.example` | Modelo de virtual host dedicado para o Nginx existente, com TLS e proxy para 8088; não instalado |
| `scripts/production/common.sh` | Projeto explícito via `-p carlosandre-portfolio-prod` e lock exclusivo |
| `scripts/production/deploy.sh`, `update.sh` | Pré-verificação obrigatória e health probe local em 8088 |
| `scripts/production/rollback.sh` | Imagens do projeto e pré-verificação obrigatória; sem downgrade automático |
| `scripts/production/preflight.sh` | Verificação somente de leitura de diretório, Docker, listeners e portas publicadas; aborta se ocupadas por terceiros |
| `scripts/tests/preflight.sh` | Testes simulados de porta livre, serviço host, container estrangeiro, projeto próprio e listener não autorizado |
| `scripts/verify-production.py` | Verificação do isolamento novo, TLS no host simulado e ensaio visual opcional com cópia descartável |
| `frontend/tests/docker-recovery.spec.cjs` | Playwright: comparação responsiva com a referência, painel, segurança, CRUD, uploads, currículo e contato |
| `docs/producao.md`, `README.md` | Manual atualizado para VPS compartilhada e fluxo de recuperação |
| `docs/prontidao-producao.md` | Marcado como registro histórico, com referência ao relatório atual |
| `docs/recuperacao-docker.md` | Este inventário e resultados da recuperação |
| `docs/recuperacao-docker-testes.json` | Resumo Playwright com rotas públicas e métricas, sem dados privados |

Os scripts de backup, restore e restore-drill preservam a lógica anterior e herdam o novo projeto pelo helper comum. O `restore.sh` de produção não foi executado.

## Topologia preparada

`Cloudflare DNS/HTTPS/WAF → Nginx existente na VPS (TLS) → 127.0.0.1:8088 → Nginx do projeto → Next.js/FastAPI → PostgreSQL exclusivo`.

Diretório previsto: `/opt/carlosandre-portfolio`. SmartFamily permanece em `/opt/smartfamily`, com seu próprio Compose. Nenhuma rede externa compartilhada, volume de terceiros, porta PostgreSQL ou porta FastAPI é usada. Os nomes de rede e volume recebem o prefixo `carlosandre-portfolio-prod_`.

O proprietário informou que 8088 estava livre em verificação anterior. A disponibilidade atual **não foi confirmada na VPS**, pois o acesso foi explicitamente vedado nesta etapa. O pré-deploy exige nova verificação e falha sem parar o ocupante. Os limites de runtime estão preparados, mas a capacidade disponível e caminhos reais dos certificados precisam de validação antes da implantação autorizada.

## Validação

- Build backend de produção: aprovado.
- Build Next.js de produção: aprovado, incluindo TypeScript e standalone.
- Validação Compose: projeto, redes e volumes exclusivos; única publicação em loopback 8088; limites de memória em todos os serviços; banco/API sem portas públicas.
- Alembic em PostgreSQL descartável: upgrade executado duas vezes, revisão `0003`, `alembic check` sem novas operações.
- Backend: **80 testes aprovados**, com um aviso de depreciação Starlette/httpx já existente.
- Persistência de uploads após recriação, reinicialização de banco e restauração de dump e mídia: aprovadas.
- Nginx: sintaxe e tráfego HTTPS através do virtual host simulado e Nginx interno aprovados. Nenhuma configuração instalada no host real.
- Produção: readiness 200, documentação API desabilitada, cookies Secure/SameSite Strict e rejeição CSRF verificados; a suíte backend cobre sessão HttpOnly, rotação, hash e expiração.
- Pré-deploy: cinco cenários simulados aprovados (porta livre; host estrangeiro; container estrangeiro; porta do projeto; listener estrangeiro mesmo com projeto existente). Nenhum serviço real tocado.
- Playwright: **16 comparações, diferença máxima de pixels 0%**, nos tamanhos 1440 e 390. Rotas: Home, Sobre, Experiência, Cases, Artigos, Privacidade, SmartFamily e artigo publicado. A Home preserva a seção de vídeos em preparação; não havia vídeo publicado para exercitar um player real.
- Playwright funcional: paridade do JSON público; login e SSR `/admin`; CSRF; CRUD/publicação; conflito de versão; upload privado com acesso anônimo negado; currículo DOCX; formulário com persistência; retry pendente sem duplicar contato; logout.
- Comparação Git: páginas/componentes/dados/assets e implementações FastAPI/PostgreSQL/Gmail mantidos iguais a `374533a`; os cinco arquivos restaurados também são idênticos à base.
- Recursos descartáveis removidos após o teste. Credenciais efêmeras do navegador removidas. Screenshots locais ficaram em `.private/carlosandre-check-6e52716b6c/visual/`; resumo sem dados privados em [recuperacao-docker-testes.json](recuperacao-docker-testes.json).

Nenhum e-mail real foi enviado; a fila de contato foi testada sem SMTP e o envio é simulado na suíte backend. SMTP real, disponibilidade atual de 8088, capacidade da VPS, certificados, virtual host existente e configuração Cloudflare continuam pendentes da próxima etapa autorizada.

Comandos repetíveis e detalhes de operação: [manual de produção](producao.md). A etapa seguinte exige autorização própria para acesso/deploy na VPS; este relatório não a presume.
