# DOCX: staging persistente, expiração e recuperação

## Diagnóstico reproduzido

Dois testes falharam na versão anterior e passam com esta correção:

1. O worker (e a abertura de outra importação) apagava imediatamente o staging ao vencer `DOCX_STAGING_MINUTES` (60 minutos por padrão). A página aberta conservava o token antigo. Antes da limpeza o commit retornava 410; depois, 404.
2. O commit carregava o staging antes de consultar o recibo. Uma confirmação já gravada voltava a retornar 404 após limpeza/recriação sem os arquivos, embora o ID do artigo estivesse no PostgreSQL.

Há também um 404 distinto quando um recibo aponta para um artigo excluído logicamente: agora esse estado é apresentado para recuperação explícita, sem criar duplicata. Não foi acessada a VPS; o corpo e a configuração efetivamente implantada precisam ser conferidos na validação posterior. O status 404 isolado não distingue esses três casos de uma versão desatualizada sem a rota.

## Persistência e correção

O Compose de produção versionado já monta o mesmo volume `media_data` em `/app/uploads` no backend e worker. Preview, render, resume e commit usam `/app/uploads/.docx-staging/<sha256-do-token>`. Next.js não armazena esses arquivos. Recriar o backend mantendo o projeto e o volume não elimina a revisão.

- A revisão validada em render é gravada atomicamente no manifesto privado; a atividade renova o prazo de uso.
- Importações não confirmadas têm uma janela privada de recuperação de 24 horas adicionais ao prazo inicial. A sessão administrativa continua sujeita à sua expiração normal e o token continua vinculado à mesma conta e sessão.
- Limpeza, retomada e salvamento usam o mesmo bloqueio PostgreSQL por documento. A limpeza confere o manifesto novamente após adquirir o bloqueio.
- `POST /api/admin/docx/staging/<token>/resume` confere sessão, CSRF e hashes antes de renovar a revisão. Nada é publicado ou confirmado automaticamente.
- Commit ausente/expirado consulta primeiro o recibo disponível para aquela sessão e devolve o ID já salvo. Registros arquivados/excluídos exigem recuperação explícita, com versão atual e nova revisão de histórico.
- Erros distinguem staging expirado, prazo encerrado e arquivos ausentes; o cliente oferece Retomar revisão e Consultar resultado.
- O token pendente é guardado desde a prévia. Após recarregar a página, Retomar revisão recupera o último checkpoint validado.
- Se os arquivos foram realmente removidos, a página ainda aberta permite reanexar o mesmo DOCX, conferindo seu SHA-256 e remapeando as mídias pelos hashes. Campos editados e posições das imagens são mantidos; é obrigatório revisar de novo antes de salvar.

Não há recuperação ilimitada: depois da janela e da limpeza, sem a página aberta nem o arquivo original, os arquivos removidos não podem ser reconstruídos. Se houver imagem substituída que não esteja no DOCX reanexado, a operação é interrompida sem apagar as edições abertas. Limites de 8 MiB por DOCX, imagens e descompressão permanecem iguais.

## Provas locais

- Build das imagens de produção do backend e Next.js, incluindo TypeScript: aprovado.
- Testes dedicados: 34 aprovados com o DOCX privado real; testes gerais: 113 aprovados, 20 ignorados por condições do ambiente. Aviso preexistente de depreciação do TestClient.
- Cliente HTTP: 11 casos aprovados, incluindo erro estruturado de staging e preservação do CSRF.
- Playwright: remove e recria o backend com o mesmo volume; confirma identidade da revisão e mídias; provoca expiração e executa a limpeza no worker, em outro container; retoma e salva.
- Provoca também expiração definitiva/remoção, reanexa o DOCX e preserva alteração editorial feita na página. Confere dez seções, quatro imagens e seus hashes.
- Repete commit após limpeza dos arquivos e recebe o mesmo ID; testa resposta incompleta, clique duplo, confirmação no editor e recuperação de arquivado.
- Capturas 1440 e 390 px; Home e artigo de controle sem diferença de pixels. Nenhum erro JavaScript ou diálogo inesperado no ensaio.

O ensaio usa imagens de produção, PostgreSQL 16, redes/volumes exclusivos e o mesmo caminho de mídia compartilhado do Compose. HTTPS, cookies Secure, CSRF e proxies são verificados separadamente; o navegador usa entrada HTTP apenas em loopback com contas sintéticas. O teste não usa credenciais, volumes ou bancos reais.

Reprodução: construir as imagens `carlosandre-docx-check-backend`, `carlosandre-production-check-backend` e `carlosandre-production-check-frontend`; executar `scripts/verify-docx-import.py`, `frontend/tests/api-errors.spec.cjs` e `scripts/verify-production.py --combined`. Documento, relatórios e screenshots ficam no diretório `.private`, fora do Git.

## Implantação posterior — não executada

Atualizar **backend, worker e frontend juntos**, com a mesma imagem/tag do backend para o worker. Um worker antigo ainda pode remover o staging segundo a política antiga. Manter o mesmo projeto `carlosandre-portfolio-prod`, o mesmo volume de mídia e o PostgreSQL existente. Não executar `down -v`, não trocar nomes de volumes e não executar limpeza de volumes.

Não há migração de schema. Reversão de código deve manter os volumes e considerar que o worker anterior volta à política de expiração antiga. Nenhum deploy, acesso à Hostinger, alteração do SmartFamily ou publicação de artigo real foi realizado nesta etapa.
