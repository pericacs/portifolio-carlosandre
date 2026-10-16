# Base administrativa — entrega de 14/10/2026

Endereço: http://localhost:8080/admin/login. Esta é a etapa inicial solicitada de inspeção e implementação da base, não a entrega de todos os módulos do CMS.

## Implementado

- Login, logout e validação de sessão pelo backend; páginas protegidas também verificam a sessão no servidor Next.js.
- Hash Argon2id reutilizando o CLI existente. Nenhum cadastro público ou senha fixa.
- Cookie de sessão HttpOnly, SameSite Strict, Secure configurável e obrigatório em produção; sessão padrão de oito horas. Banco armazena hashes dos tokens, não seus valores.
- Rotação de tokens no login e revogação no logout; contas desativadas e sessões expiradas não acessam o painel.
- CSRF com validação de origem exata, cookie/token e hash associado à sessão; login e recuperação também exigem origem e token.
- Limites persistentes e atômicos: cinco tentativas por conta e 30 por peer em 15 minutos. Atrás do Nginx o limite por peer é compartilhado, pois o backend não confia em IP encaminhado pelo cliente. Não há bypass por `X-Forwarded-For`.
- Recuperação por e-mail quando SMTP estiver configurado, com resposta genérica, token de uso único e validade de 30 minutos. Redefinir a senha invalida as sessões e os links pendentes. O token fica no fragmento da URL para não entrar nos logs HTTP.
- Dashboard responsivo, menu, auditoria e página de segurança. Indicadores e conteúdos recentes são consultas reais ao PostgreSQL. Visitas não são inventadas; analytics aparece como não conectado.
- Migração aditiva `0002`, backup restaurado e comparado, documentação de migração gradual.

## Primeiro acesso

Não havia conta administrativa ativa no ambiente. Os testes criaram uma conta aleatória temporária, removida ao final; ela não é uma credencial utilizável.

Execute na raiz do projeto:

```powershell
docker compose exec backend python -m app.cli create-admin
```

Informe seu e-mail e uma senha exclusiva de pelo menos 14 caracteres no terminal. A senha não aparece na tela nem fica no histórico do comando. Depois abra `/admin/login`.

## E-mail e manutenção

Configure no `.env`: `SMTP_HOST`, `SMTP_PORT` (padrão 587), `SMTP_FROM_EMAIL`, `SMTP_USERNAME`, `SMTP_PASSWORD` e `SMTP_USE_STARTTLS=true`. Reinicie o backend para aplicar. `SITE_URL` precisa ser a origem real usada no navegador. Em produção, configure HTTPS, `APP_ENV=production` e `COOKIE_SECURE=true`.

SMTP não foi configurado nem foram enviados e-mails reais nesta entrega. O caminho de recuperação e o adaptador SMTP foram testados com envio simulado; a integração real depende das credenciais do servidor. Sem SMTP, a interface informa a indisponibilidade.

`ADMIN_SESSION_HOURS` permite de 1 a 24 horas. Para remover tokens e contadores expirados sem apagar contas ou auditoria:

```powershell
docker compose exec backend python -m app.cli prune-auth
```

Inclua esse comando na rotina operacional quando o ambiente for publicado. Auditoria não contém senhas, tokens ou corpos de mensagens SMTP.

## Testes e evidências

- Build Docker/Next.js e TypeScript.
- 27 testes pytest aprovados com PostgreSQL real, transações revertidas, cobrindo a base anterior e autenticação: rotas protegidas, cookies, rotação, logout, CSRF, origem, rate limit, expiração, conta desativada, dashboard, recuperação, uso único, revogação, SMTP simulado e manutenção. Houve um aviso de depreciação do adaptador httpx do TestClient, sem falhas.
- Alembic sem divergências; restauração, comparação das 25 tabelas existentes e upgrade/downgrade/upgrade em banco separado.
- Playwright em 1440 e 390 px: login, sessão, dashboard, menu mobile, auditoria, segurança, logout, acesso não autenticado e redefinição de senha por link temporário de teste.
- Comparação das capturas completas da Home antes/depois: zero canais de pixels diferentes em ambas as larguras. Sem erros JavaScript.

Capturas em `docs/screenshots/admin/`: `dashboard-1440.png`, `dashboard-390.png`, `login-1440.png`, `login-390.png`, auditoria, menu mobile e Home antes/depois. `playwright-report.json` registra a comparação.

Repetir:

```powershell
docker compose exec backend python -m pytest -q -p no:cacheprovider
docker compose exec backend alembic check
node frontend/tests/admin.spec.cjs
```

Para Playwright, disponibilize os módulos `playwright` e `sharp` no Node ou indique seus caminhos com `PLAYWRIGHT_MODULE` e `SHARP_MODULE`. O teste precisa do Docker CLI e cria/remove apenas seu administrador temporário. As capturas de referência devem corresponder à versão pública cuja aparência se deseja preservar.

## Roteiro manual

1. Sem login, abrir `/admin` e `/admin/auditoria`: deve redirecionar ao login.
2. Criar sua conta pelo CLI e entrar. Conferir os quatro projetos existentes e os demais indicadores reais.
3. Abrir Registro de operações e conferir `auth.login`.
4. Em 390 px, abrir o menu e navegar; não deve haver rolagem horizontal da página.
5. Sair e tentar reabrir uma rota protegida: deve exigir login.
6. Com SMTP configurado, solicitar recuperação, abrir o link, redefinir a senha e verificar que ele não funciona novamente.
7. Conferir a Home e a fotografia atual: nenhum componente público foi alterado.

## Arquivos principais

Backend: `app/admin.py`, `app/main.py`, `app/models.py`, `app/config.py`, `app/cli.py`, `alembic/versions/0002_admin_auth.py`, `tests/test_admin.py`.

Frontend: `src/app/admin/`, `src/components/admin/`, `src/lib/admin-server.ts`, `tests/admin.spec.cjs`. Os estilos são CSS Modules limitados ao painel. Nenhum arquivo de layout, estilo ou conteúdo da Home foi modificado.

Configuração/documentação: `.env.example`, `README.md`, `docs/admin-migration-plan.md`, este documento e screenshots. Sem novas bibliotecas de runtime.

## Próximas etapas ainda não implementadas

CRUDs de perfil, currículo, skills, projetos, artigos, vídeos, cases e configurações; upload de mídia/currículo; editor rico e revisões; preview editorial; agendamento com worker; integração do conteúdo público com o banco; formulário conectado, antispam, retenção e política de privacidade. Os itens do menu sob “próximas etapas” são indicação de escopo, não botões de funcionalidades concluídas.
