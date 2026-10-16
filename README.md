# Carlos André | Technology & Ventures

Implementação por fases conforme `docs/requisitos-originais.txt`.

**Estado: Home e CMS completo implementados para validação local.** Perfil, currículo, experiências, formação, certificações, idiomas, skills, categorias, projetos, cases, artigos, vídeos, mídia, mensagens e configurações persistem no PostgreSQL. O painel reutiliza a autenticação existente e oferece rascunhos, preview autenticado, publicação, agendamento e histórico. Consulte `docs/cms-completo.md`. Não houve publicação em `carlosandre.tech`.

Veja `docs/fase-2.md` para arquivos alterados, fontes, screenshots reais, testes e limitações. A data final da Compass UOL está marcada para validação. O currículo original fica em `docs/private/` (não servido pelo frontend); o download público é uma cópia sem endereço residencial.

## Ambiente local

Requisito: Docker Desktop com containers Linux e Docker Compose v2. Não é necessário instalar Node ou Python no computador quando se utiliza Docker.

Na raiz do projeto, em PowerShell:

```powershell
./scripts/setup.ps1
docker compose up -d --build
docker compose exec backend python -m app.import_cms
```

O script preserva um `.env` existente. Em outros sistemas, copie `.env.example` para `.env` e preencha `POSTGRES_PASSWORD` com uma senha aleatória de pelo menos 16 caracteres. O `.env` nunca deve ser versionado.

- Aplicação: http://localhost:8080
- Documentação da API: http://localhost:8080/api/docs
- Prontidão da API e do banco: http://localhost:8080/api/health/ready

Somente o Nginx publica uma porta, restrita a `127.0.0.1`. PostgreSQL, frontend e API comunicam-se pela rede interna do Compose. Dados do banco e mídia permanecem em volumes próprios deste projeto. O serviço `migrate` executa `alembic upgrade head` antes da API iniciar.

Para desenvolvimento com recarregamento automático:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
```

Após alterar dependências do frontend, atualize também o volume de dependências via `docker compose -f compose.yaml -f compose.dev.yaml exec frontend pnpm install --frozen-lockfile`.

Para parar preservando dados: `docker compose down`. Não utilize `down -v` quando precisar preservar banco e mídia.

## Primeiro administrador

```powershell
docker compose exec backend python -m app.cli create-admin
```

O terminal solicita e-mail, senha e confirmação. A senha exige pelo menos 14 caracteres e é armazenada como hash Argon2id. Não há conta ou senha administrativa padrão. O comando recusa e-mail duplicado e registra a criação na auditoria. A base administrativa já está disponível em `http://localhost:8080/admin/login`, com sessões, CSRF, rate limiting, dashboard e auditoria. Os módulos editoriais estão disponíveis. Veja `docs/cms-completo.md` e `docs/admin-migration-plan.md`.

## Dados iniciais

`python -m app.import_cms` importa 117 registros documentados como rascunhos, com chaves de origem estáveis. Reexecutar não sobrescreve edições nem recria registros excluídos. A versão estática aprovada permanece como base pública; somente publicações explícitas no painel a substituem por registro. Arquivar ou excluir também retira a respectiva versão da base pública. Datas da Compass e confidencialidade dos cases continuam sujeitas a revisão.

## Verificação

```powershell
docker compose exec backend python -m pytest -q -p no:cacheprovider
docker compose exec backend alembic check
docker compose ps
```

Os testes precisam do PostgreSQL migrado e usam transações revertidas. Execute em ambiente de desenvolvimento. Validam integridade relacional, restrições editoriais, datas simultâneas, seed, criação administrativa, Argon2id, consentimento e saúde da API. A suíte CMS cobre CRUDs, snapshots, agendamento, uploads, permissões, sanitização e contatos. O Playwright está em `frontend/tests/cms.spec.cjs`.

O build de frontend verifica TypeScript. Para executar fora do Docker, use Node 22+ e pnpm 11.19.0 em `frontend`: `pnpm install --frozen-lockfile` e `pnpm build`. A API usa Python 3.12 no Docker, SQLAlchemy 2 e Alembic. O frontend usa Next.js 16, React 19 e Tailwind 4, com resolução de dependências registrada em `pnpm-lock.yaml`.

## Estrutura

| Diretório | Responsabilidade |
|---|---|
| `frontend/src/app` | Next.js App Router e tokens visuais iniciais |
| `frontend/public/images` | Foto fornecida pelo proprietário |
| `backend/app` | Configuração, conexão, modelos SQLAlchemy Core, API de saúde, CLI e seed |
| `backend/alembic` | Migrações explícitas e versionadas |
| `backend/tests` | Testes de integração com PostgreSQL |
| `infra/nginx` | Proxy local e cabeçalhos básicos |
| `docs/references` | Imagens originais preservadas |
| `docs/fase-1.md` | Decisões, validações e pendências da etapa |

## Próximas fases e produção

A Home, as páginas profissionais e os módulos CMS estão disponíveis localmente. Conteúdos editoriais planejados continuam identificados como tal. Traduções, URLs reais de vídeos e revisão de dados devem ser fornecidas pelo proprietário; o painel permite sua edição e publicação. SMTP, YouTube Data API e analytics dependem de configuração externa; nenhum número de visitas foi inventado.

O Compose atual é **local**. TLS, Cloudflare, configuração para `carlosandre.tech`, backups automáticos, SMTP e analytics não foram ativados. A API rejeita uma configuração declarada como produção sem HTTPS e cookies Secure, mas essa validação isolada não torna a aplicação pronta para produção.

As referências técnicas utilizadas na estrutura são a [instalação oficial do Next.js](https://nextjs.org/docs/app/getting-started/installation) e o [tutorial oficial do Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
