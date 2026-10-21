# Homologação local — importação DOCX

Data: 21/10/2026. Branch: `codex/docx-article-import`, baseada em `258cef8`. Sem deploy, acesso à VPS ou alterações no PostgreSQL original. Branches Docker, segurança e Cloudflare preservadas.

## Documento real

`Artigo_Split_do_Mal_Completo_Illustrado.docx`, copiado somente para a área privada de teste. SHA-256: `ba394da4286d552f1d68b74c96945e3efc9a92dc1eac158ff90ded6e70448487`.

| Verificação | Resultado |
| --- | --- |
| Título | O SPLIT DO MAL |
| Subtítulo | Quando o imposto chega antes do dinheiro necessário para manter sua empresa viva |
| Autor | Carlos André Cardoso dos Santos |
| Estrutura | Dez seções numeradas, referências e dois subtítulos internos |
| Mídias | Quatro imagens: capa e três diagramas intercalados |
| Integridade | Os quatro hashes extraídos coincidem com os arquivos incorporados no ZIP |
| Legendas | Três legendas VISUAL 1, 2 e 3, próximas dos respectivos diagramas |
| Citações | Três caixas de citação preservadas como blockquotes |
| Fontes | Três URLs originais convertidas em links HTTP(S) seguros |
| Tags | Hashtags explícitas do documento aproveitadas como sugestões |
| Data | 19/10/2026 encontrada em nota de atualização, com alerta de confirmação |
| Publicação | Importação cria rascunho; publicação depende de ação separada |

A capa anterior ao título foi movida ao cabeçalho; título, subtítulo e assinatura não se repetem no corpo. As tabelas do documento real eram caixas de citação com uma célula; tabelas de dados, listas, notas e formatação também foram validadas com documentos sintéticos.

## Evidência automatizada

- Parser/API DOCX com o documento real: **25 testes aprovados** em PostgreSQL descartável.
- Suíte geral: **105 aprovados, 19 pulados**. Os testes que exigem o pacote editorial privado e o DOCX privado não são executados pela suíte geral sem seus mounts.
- Pacote editorial PostgreSQL em ensaio offline separado: **19 aprovados**, com pacote montado somente para leitura e rede desabilitada.
- Builds Docker de produção do backend e frontend aprovados. O build limpo Next.js concluiu TypeScript e a geração standalone.
- Alembic upgrade repetido e `alembic check` aprovados, permanecendo na revisão `0003`, sem nova migração.
- Persistência de banco/mídias, dump e restauração em banco/volume descartáveis, cookies Secure/SameSite, CSRF, health checks, worker e cadeia Nginx HTTPS aprovados pelo verificador de produção.
- Falhas de persistência e disco, resposta perdida após commit, retries, colisões de slug, versão concorrente, cancelamento, expiração, acesso por outra sessão, upload inválido, XSS, conteúdo ativo, ZIP bomb e XML malicioso cobertos.
- Há um aviso de depreciação do TestClient Starlette/httpx; não houve falha funcional associada. A atualização dessa dependência não faz parte desta funcionalidade.

Os números das suítes não devem ser somados: existem testes em comum.

## Navegador e comparação editorial

Playwright executa o fluxo real pelo painel: login, botão de importação, envio do DOCX, campos preenchidos, confirmação inicialmente bloqueada, prévia, confirmação de revisão, rascunho, histórico, mídia privada e publicação explícita **somente no banco descartável**. Verifica imagens carregadas, proporção original, ausência de overflow em 1440 e 390 pixels, links, títulos, legendas e ampliação do diagrama. Os bytes das mídias persistidas são conferidos por SHA-256.

Capturas da prévia de importação, do rascunho e da página pública foram produzidas em desktop e mobile na área `.private/`. A inspeção visual confrontou a sequência OOXML e as imagens extraídas do original com a página: capa, introdução, seções 1–2, VISUAL 1, seções 3–5, VISUAL 2, seções 6–7, VISUAL 3, seções 8–10 e referências. Diagramas mantêm a proporção e podem ser ampliados no celular.

O teste compara Home e um artigo anterior sintético antes/depois da importação/publicação. Não é uma comparação pixel a pixel contra todas as referências históricas aprovadas: esses arquivos de referência não integram este ensaio. Não houve modificação de CSS global, fotografia, assets públicos, composição da Home ou dados existentes. O artigo anterior usa o caminho de renderização existente; a nova apresentação de subtítulo é restrita a artigos marcados como importados.

As quatro comparações (duas rotas em duas larguras) tiveram diferença de pixels igual a **zero**. Evidências privadas da execução final: `.private/carlosandre-check-c116f3573d/visual/`, incluindo `report.json` e capturas `article-public-1440.png` e `article-public-390.png`. Containers, redes e volumes desse ensaio foram removidos ao final.

Não foi feita rasterização das páginas originais do Word. A equivalência verificada é da ordem editorial, textos, legendas e imagens; paginação, fontes e margens do Word não são reproduzidas na página responsiva.

## Arquivos da implementação

| Área | Arquivos |
| --- | --- |
| Extração e staging | `backend/app/docx_parser.py`, `backend/app/docx_import.py` |
| Integração backend | `config.py`, `main.py`, `cms_schema.py`, `worker.py`, `requirements.txt` |
| Interface | `frontend/src/components/cms/docx-import.tsx`, `workspace.tsx`, `editor.tsx` |
| Rotas | rota administrativa dinâmica e página pública `artigos/[slug]/page.tsx` |
| Provas | `backend/tests/test_docx_import.py`, `frontend/tests/docx-import.spec.cjs`, `scripts/verify-docx-import.py`, modo `--docx` de `scripts/verify-production.py` |
| Operação | `.env.production.example` e `docs/importacao-docx.md` |

O editor manual permanece disponível; seu comportamento padrão é preservado. Na revisão da importação, uploads independentes são desabilitados para impedir arquivos órfãos fora da transação. Documentos, pacotes editoriais, arquivos extraídos, credenciais sintéticas, logs e screenshots permanecem privados e fora do Git.

## Limitações e atualização

Conversões complexas de Word exigem revisão editorial: EMF/WMF/SVG não são aceitos; GIF/TIFF geram PNG estático com aviso; mesclagem vertical, campos complexos e paginação podem exigir ajuste. Não há classificação semântica por IA nem criação de fatos ausentes.

O procedimento de atualização e rollback exclusivo do projeto `carlosandre-portfolio-prod`, incluindo preflight de 8088, backup privado e preservação de imagens anteriores, está em [importacao-docx.md](importacao-docx.md). Nenhum desses comandos foi executado no servidor. Publicação da branch e atualização da VPS ficam para a etapa de revisão/autorização.
