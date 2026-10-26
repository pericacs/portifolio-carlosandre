# Entrega conjunta: AVALLOW + DOCX

Branch `codex/avallow-production`: integração da base Docker/PostgreSQL `258cef8`, AVALLOW aprovado e importador DOCX `7ee066d`. Histórico anterior preservado, sem reset ou push forçado.

O acesso autorizado `ssh root@187.77.248.237` falhou com `Permission denied (publickey,password)`. Nenhuma nova tentativa com senha/chave foi feita. **Não houve deploy nesta execução.** A consulta HTTPS somente de leitura retornou 200 para Home, login e API pública; a Home ainda não mostrava AVALLOW. Portanto a entrega não foi declarada concluída em produção.

O arquivo único de implantação é gerado a partir de `scripts/production/deploy-portfolio-combined.sh`, com `__RELEASE_COMMIT__` substituído pelo hash completo do commit entregue. O arquivo pronto acompanha a resposta, fora do Git; não contém credenciais. Executar seu conteúdo integral pelo terminal da Hostinger. Ele busca o commit já enviado ao GitHub; não exige outra etapa de conversa.

## Comportamento do script

- Diretório obrigatório `/opt/carlosandre-portfolio`, projeto obrigatório `carlosandre-portfolio-prod`, trava de operação, árvore limpa e validação de ancestralidade Git. Recusa descartar alterações ou commits próprios do servidor.
- Não entra no SmartFamily, não muda DNS/Cloudflare/Nginx e não altera `.env.production`.
- Requer Docker Compose/Buildx, Git, Python 3, curl, flock, 1.536 MiB de memória disponível e 6 GiB livres. Recusa o build se faltar margem para os serviços existentes. O builder temporário próprio limita RAM a 1 GiB e CPU a 0,75; não troca o builder global.
- Constrói as imagens antes de parar aplicações. Guarda IDs/tags das imagens antigas e uma única fotografia privada do registro AVALLOW com hashes dos demais registros CMS, em `.private/releases/`. Não faz dump completo repetitivo de banco ou mídias.
- Exige schema Alembic `0003`; não executa migrations, importadores editoriais, criação/recriação de banco nem remoção de volumes.
- Atualiza somente backend, frontend e worker do portfólio, usando `--no-deps`. PostgreSQL e Nginx mantêm seus IDs; uploads continuam no volume existente. O override persistente fica em `.private/compose.portfolio-release.yml` e deve continuar incluído nas operações futuras desses três serviços.
- Publica exclusivamente os cinco campos aprovados do AVALLOW sobre sua publicação anterior ou baseline. Mantém conteúdo detalhado já público e preserva edições pendentes em rascunho. Não publica artigos nem outros rascunhos. Mantém ID/slug/source key OnStar, revisões e auditoria.
- Verifica pelo HTTPS real a Home, imagem, painel autenticado, envio DOCX, dez seções, quatro imagens com hashes, HTML de prévia e cancelamento. Usa uma sessão de cinco minutos auditada de administrador já ativo, revogada ao terminar. Não lê senha, não cria usuário e não salva/publica artigo. O DOCX de teste remoto é sintético; o documento real privado foi homologado localmente e não é enviado ao GitHub.
- Só imprime `VERIFIED` se as verificações reais passarem. Em falha após trocar aplicações, tenta restaurar exclusivamente os campos deste release e imagens anteriores. Se detectar edição concorrente, recusa sobrescrevê-la e mantém os logs privados. Não restaura banco inteiro nem exclui histórico.

## Evidências locais

- Builds produção backend/Next.js e TypeScript aprovados.
- Documento real `Artigo_Split_do_Mal_Completo_Illustrado.docx`: 25 testes parser/API aprovados; título/autor/subtítulo, dez seções, quatro imagens, legendas, referências e hashes preservados.
- Suíte geral: 105 aprovados; 19 opcionais pulados por dependerem de fixtures privadas não montadas nessa suíte. O teste real é executado separadamente.
- Playwright desktop/mobile: importação, revisão obrigatória, rascunho e publicação explícita apenas no banco descartável. Home e artigo anterior de controle mantêm zero diferença visual antes/depois; a homologação AVALLOW anterior também teve zero pixels alterados fora desse card em 1440/390 px.
- Manutenção PostgreSQL descartável: não publicação de rascunhos pendentes, preservação da publicação anterior, idempotência, restauração exata do registro alvo, histórico, proteção contra edições concorrentes e demais registros CMS inalterados.
- Ensaio conjunto inclui chamada HTTP autenticada através do Nginx, upload, imagens, prévia, cancelamento e revogação de sessão, além do rollback alvo.
- Sintaxe Bash/Python e opções do builder limitado verificadas localmente.

Os testes descartáveis não equivalem a uma validação em produção. O resultado real permanece pendente até executar o script na VPS e obter `VERIFIED`; falhas de Git, recursos, Cloudflare/WAF ou aplicação são reportadas, sem modificar as proteções externas para fazer o teste passar.
