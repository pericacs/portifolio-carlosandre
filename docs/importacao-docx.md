# Importação de artigos Word

Implementação local na branch `codex/docx-article-import`, derivada da versão Docker `258cef8`. O editor existente continua disponível. A entrada principal de artigos passa a ser **Importar artigo do Word**, em `/admin/artigos`.

## Fluxo

1. Enviar DOCX autenticado. A aplicação valida ZIP, XML, relações e imagens sem executar Office ou buscar recursos externos.
2. Revisar título, subtítulo, autoria, data, resumo, categorias, tags, SEO, corpo, capa e legendas. É possível substituir imagens e mudar sua posição no corpo.
3. Gerar a prévia com o HTML sanitizado pelo servidor e confirmar a revisão.
4. Salvar **rascunho**. Publicar continua sendo uma ação separada no editor existente.

O arquivo DOCX original não é persistido. Imagens e manifesto temporários ficam no volume de mídia, em `.docx-staging`, acessíveis somente à sessão que iniciou a importação. Expiram após 60 minutos; o worker reconcilia e limpa esse material. Cancelar descarta a área temporária. Backups desse volume devem continuar privados.

Repetir a confirmação retorna o recibo existente. Reenviar o mesmo documento também evita duplicação por padrão. Para criar outro artigo ou uma versão é necessária uma decisão explícita. Uma nova versão mantém o conteúdo publicado anterior e cria um rascunho; eventual agendamento anterior é cancelado com aviso. Alterações concorrentes são recusadas por versão.

Registro editorial, revisões, auditoria, referências de mídias e recibos são gravados na mesma transação PostgreSQL. Arquivos finais usam nomes UUID exclusivos e hard links no mesmo volume. Em falhas, a reconciliação consulta os registros confirmados antes de remover links próprios: não apaga arquivos de um commit cuja resposta foi perdida. O worker recupera também interrupções do processo. As URLs temporárias não são salvas no conteúdo definitivo.

## Limites e configuração

- DOCX até 8 MiB, 1.000 entradas ZIP, 50 MiB descompactados e 100.000 elementos por XML.
- Até 32 imagens únicas, 8 MiB por arquivo incorporado e 25 megapixels por imagem.
- PNG, JPEG e WebP preservam os bytes. GIF/TIFF são convertidos ao primeiro quadro/página PNG com aviso. EMF, WMF e SVG exigem conversão prévia e são recusados.
- Macros, ActiveX, objetos OLE, arquivos executáveis, entidades XML e relações inseguras são recusados. Imagens externas não são baixadas.
- Cabeçalhos e rodapés não entram no corpo. Notas de rodapé/finais são anexadas como referências navegáveis. Mesclagem vertical de tabelas gera alerta de revisão. Equações, campos automáticos complexos, caixas flutuantes e paginação do Word não têm equivalência garantida no HTML.
- Metadados ausentes são sinalizados. Categorias e hashtags explícitas são aproveitadas; nenhuma autoria ou data é inventada. Datas em notas de atualização exigem confirmação editorial.

Variáveis opcionais: `DOCX_DEFAULT_AUTHOR`, `DOCX_DEFAULT_CATEGORY`, `DOCX_DEFAULT_TAGS` (array JSON) e `DOCX_STAGING_MINUTES` (10–1440). Defaults preenchidos por configuração também devem ser revisados.

Sessão, CSRF, origem permitida, rate limit e controle de publicação são os mecanismos existentes do CMS. Não há nova migração Alembic: a revisão permanece `0003`. Recibos usam configurações internas, não a API pública de conteúdo.

## Reprodução local

```powershell
docker build -f backend/Dockerfile.prod -t carlosandre-docx-check-backend backend
docker build -t carlosandre-docx-check-frontend frontend
python scripts/verify-docx-import.py
docker tag carlosandre-docx-check-backend carlosandre-production-check-backend
docker tag carlosandre-docx-check-frontend carlosandre-production-check-frontend
python scripts/verify-production.py --docx
```

Playwright e Sharp devem estar resolvíveis no Node, ou indicados por `PLAYWRIGHT_MODULE` e `SHARP_MODULE`. O teste real usa uma cópia privada em `.private/docx-import-check/reference.docx` (ou `DOCX_REFERENCE` para o teste de navegador). Não versionar o documento, suas imagens extraídas, contas sintéticas, screenshots ou logs. O ensaio cria redes, banco, conta e volumes exclusivos, publicando somente uma porta aleatória em loopback, e remove seus recursos ao terminar. O modo `--docx` não copia o PostgreSQL original.

## Atualização futura exclusivamente do portfólio

**Procedimento documental; nada foi executado na VPS.** Revisar e aprovar primeiro a branch e o relatório. Publicar a branch no GitHub somente com arquivos de código, testes e documentação. Não transferir `.private`, `.env`, uploads locais ou o DOCX de homologação.

Na VPS, após autorização para atualização e com a branch disponível remotamente:

```bash
cd /opt/carlosandre-portfolio
test "$(pwd -P)" = /opt/carlosandre-portfolio || exit 1
git status --short                 # interromper se houver alterações não revisadas
git fetch origin
git switch codex/docx-article-import
git pull --ff-only origin codex/docx-article-import
git rev-parse HEAD                 # conferir o commit aprovado
bash scripts/production/preflight.sh
```

Conferir `.env.production` existente sem mostrá-lo em logs, especialmente `RELEASE_TAG`: escolher um novo identificador e registrar o anterior. Preservar as imagens anteriores. O preflight exige porta 8088 livre ou pertencente ao Nginx deste projeto. Se houver divergência, interromper.

```bash
# Com a tag nova já configurada de forma privada:
bash scripts/production/update.sh
docker compose -p carlosandre-portfolio-prod --env-file .env.production \
  -f docker-compose.prod.yml ps
curl --fail http://127.0.0.1:8088/api/health/ready
```

O script cria backup privado do banco e de todas as mídias com SHA-256, pausa somente os escritores do projeto `carlosandre-portfolio-prod`, executa Alembic e sobe backend/frontend/worker/Nginx desse projeto. Há uma breve indisponibilidade do portfólio. Não usar comandos globais `docker stop`, `prune` ou `compose down -v`; não entrar em `/opt/smartfamily`. Nginx do host, DNS, Cloudflare e serviços de outros projetos não precisam de alteração para esta funcionalidade.

Homologar login, importação, prévia, rascunho, imagens e histórico antes de publicar qualquer artigo real. Conferir também um artigo antigo, Home e envio de contato.

## Rollback

Em falha do importador, não repetir com remoção manual de registros ou arquivos: repetir a confirmação padrão usa o recibo idempotente. Se necessário descartar somente a importação temporária pelo painel.

Para rollback da aplicação, usando a tag anterior registrada:

```bash
bash scripts/production/rollback.sh TAG_ANTERIOR_APROVADA
```

O rollback troca somente as imagens da aplicação deste projeto, sem rebaixar schema ou restaurar dados automaticamente. Mantenha a tag anterior também em `RELEASE_TAG` após a reversão. Rascunhos e recibos novos permanecem no banco. Uma restauração de backup exige autorização separada, ensaio em banco/volume descartáveis e preservação das alterações feitas depois do backup; não sobrescrever produção como resposta automática a uma falha de interface.
