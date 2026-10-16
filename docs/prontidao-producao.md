# Relatório de prontidão — 16/10/2026

**Resultado: preparação concluída e validada localmente; liberação pública condicionada à homologação na VPS. Nenhum deploy executado.** Design, Compose local, credenciais e dados locais preservados. Nenhuma credencial real foi incluída nas alterações.

## Entregas

| Requisito | Implementação |
|---|---|
| Builds de produção | Next.js standalone multi-stage já existente, backend com wheels multi-stage e usuário sem root; contexto de build exclui segredos e uploads |
| Isolamento | `docker-compose.prod.yml`, projeto fixo `carlosandre-production`, redes e volumes próprios |
| Variáveis | `.env.production.example` apenas com placeholders; arquivo real ignorado pelo Git |
| Proxy e TLS | Nginx para domínio canônico, redirecionamento HTTPS, TLS 1.2/1.3, headers e resolução dinâmica Docker |
| Saúde e reinício | PostgreSQL, API, Next.js, Nginx e heartbeat do worker; `unless-stopped` para processos persistentes |
| Persistência | Volumes exclusivos para PostgreSQL e uploads compartilhados pela API e worker |
| Rede e portas | PostgreSQL em rede interna; apenas Nginx publica 80/443; API, banco e frontend sem portas no host |
| Cloudflare | Procedimento Full (strict), Origin CA/CA pública, bypass de cache administrativo e regras de firewall documentados |
| Administração | Secure, HttpOnly na sessão, SameSite Strict, hashes, CSRF por origem e sessão já existentes; CORS de produção agora exige origem canônica exata |
| Gmail | Configuração exclusivamente por variáveis, STARTTLS obrigatório em produção; fila preservada sem configuração |
| Logs | json-file, 10 MB × 5 arquivos por serviço |
| Backup e restore | Dump custom, tar de uploads, checksums, manifesto de imagens; pausa de escritores; restauração e ensaio em volumes descartáveis |
| Migrações | Advisory lock, transação PostgreSQL e limites de espera/execução; atualização faz backup antes de migrar |
| Operação | Scripts Bash para deploy inicial, atualização, rollback compatível, backup, restore e ensaio; lock entre operações |
| Verificação | `scripts/verify-production.py`, independente do `.env` e da stack local |

## Evidências locais

- Build Docker backend: aprovado com Python 3.12 e dependências fixadas.
- Build Docker frontend: aprovado; Next.js 16, TypeScript e geração standalone concluídos.
- Validação do Compose com arquivo de exemplo: aprovada; nenhuma porta pública da API/PostgreSQL; rede privada marcada como interna.
- PostgreSQL 16 descartável: `alembic upgrade head` executado duas vezes; `alembic check` sem novas operações; revisão `0003` preservada após reinício.
- Suíte completa backend: **80 passed**, com um aviso de depreciação Starlette/httpx já existente. A asserção antiga de projetos no dashboard foi alinhada ao CMS, assim como já ocorria com experiências; nenhum comportamento de produto alterado.
- Persistência de uploads: escrita em container, leitura em novo container com mesmo volume; arquivo preservado.
- Recuperação: dump custom restaurado em outro banco, revisão `0003` confirmada; tar de mídia restaurado em outro volume e conteúdo conferido.
- Segurança em modo production: readiness 200, documentação 404, cookie CSRF Secure/SameSite Strict e login sem origem/CSRF recusado com payload válido. A suíte existente cobre cookie de sessão HttpOnly, hash, expiração, rotação, CSRF e autenticação.
- Inicialização real de frontend, API e worker em rede descartável; heartbeat recente confirmado.
- Nginx: `nginx -t` aprovado com certificado temporário; requisições HTTPS com validação da CA de teste retornaram 200 para `/` e `/api/health/ready` através do proxy.
- Scripts operacionais: sintaxe validada em Bash Linux; finais de linha LF fixados por `.gitattributes`.
- Recursos temporários do verificador removidos no bloco de limpeza. Nenhuma porta de teste publicada, nenhum dado da base local usado, nenhuma mensagem real enviada.

Os testes exercitaram os componentes de backup/restauração em Docker isolado. Os scripts completos de deploy, atualização, rollback e recuperação de produção não foram executados contra a VPS, conforme o escopo desta etapa. O ensaio `restore-drill.sh` está disponível para validar o primeiro backup operacional.

## Condições antes do go-live

1. Provisionar VPS exclusiva, configurar acesso administrativo, firewall compatível com Docker e IPv6, e validar portas externamente.
2. Gerar credenciais inéditas, instalar certificado/chave na VPS e configurar DNS/Cloudflare Full (strict), bypass de cache e proteção do origin.
3. Executar deploy autorizado na próxima etapa, criar administrador e importar somente o conteúdo versionado aprovado.
4. Validar Gmail real, recuperação administrativa, fila, uploads após recriação e fluxos públicos; políticas da conta podem impedir senha de app.
5. Executar backup operacional e `restore-drill.sh`; medir RTO, definir RPO/retenção e enviar cópia criptografada para armazenamento externo.
6. Configurar cron de backup, logrotate do log operacional e alertas de certificados, disco, filas e containers unhealthy. Health check sozinho não reinicia processo travado.
7. Registrar SHA e tags por release, preservar imagens anteriores e revisar compatibilidade do schema antes de rollback. Não há downgrade automático nem backup remoto configurado nesta etapa.

Procedimentos e fontes oficiais: [manual de produção](producao.md).
