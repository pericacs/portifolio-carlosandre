# DOCX: confirmação, navegação e recuperação

## Diagnóstico e escopo

Na versão inspecionada o HTTP 200 de commit contém `{entry: {id, status, ...}, status}`. Não foi capturada uma resposta autenticada da produção; os logs 200 informados não demonstram seu corpo. O contrato foi confirmado com o backend real no ensaio local.

O cliente acessava `result.entry.id` sem validação e fazia uma navegação completa enquanto o bloqueio `beforeunload` permanecia ativo. Uma resposta incompleta ou falha de navegação caía no erro genérico, mesmo após o banco confirmar. Um recibo anterior também podia devolver um artigo arquivado sem explicar esse estado.

## Correção

- Resposta mantém `entry` e acrescenta `entryId`; cliente aceita ambos e valida UUID.
- Navegação pelo roteador Next para `/admin/artigos/<id>?docx=saved`, com confirmação no editor e bloqueio de saída desativado após confirmação.
- Trava síncrona contra cliques repetidos; idempotência transacional existente preservada.
- Consulta autenticada `GET /api/admin/docx/staging/<token>/result` recupera o artigo após resposta perdida, inclusive após limpeza do staging para novos recibos. Token pendente fica no sessionStorage; documento e conteúdo não são guardados no navegador.
- Recibos novos vinculam proprietário e sessão. Esses identificadores não são devolvidos em histórico ou prévia. Recibos antigos dependem do staging ainda válido para comprovar a sessão.
- Artigo arquivado oferece abrir ou recuperar como rascunho. Recuperação explícita exige sessão, CSRF, correspondência com a importação e versão atual, mantém ID, conteúdo, mídias e revisões e acrescenta revisão de recuperação. Nada é publicado.
- Sem alteração de schema, parser, design público ou outros projetos.

## Verificação local

- Build Docker de backend e frontend; TypeScript integrado ao build Next aprovado.
- Suíte dedicada: 29 testes aprovados, com DOCX real privado.
- Suíte geral: 107 aprovados, 20 ignorados por condições do ambiente; aviso de depreciação preexistente do TestClient.
- Playwright com o documento real: dez seções, quatro imagens e hashes conferidos; salva rascunho, mostra confirmação e abre o editor.
- Resposta HTTP 200 propositalmente incompleta após commit real: recupera por GET sem novo POST; dois cliques síncronos resultam em um commit.
- Resposta normal 200 e reimportação do mesmo documento abrem o mesmo registro; arquivado é recuperado com o mesmo ID e dados.
- Capturas desktop 1440 e mobile 390; Home e artigo anterior com diferença de pixels zero. Sem diálogos inesperados ou erros JavaScript.
- PostgreSQL, volumes e contas usados nos testes são descartáveis e exclusivos. Nenhum deploy, acesso à VPS ou alteração de dados reais.

Os relatórios e capturas permanecem no diretório privado local de testes e não são versionados. A confirmação em produção depende da implantação posterior autorizada.
