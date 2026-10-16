# Fase 1 — Estrutura, banco e ambiente local

## Inspeção

A pasta de trabalho estava vazia. Não havia repositório Git, aplicação, arquivos AGENTS.md locais ou dados preexistentes para migrar. Os arquivos enviados foram copiados sem edição; seus hashes SHA-256 foram comparados com os originais.

- `docs/references/portfolio-aprovado.png`: referência de composição integral.
- `docs/references/carlos-andre-original.jpg`: foto real original.
- `frontend/public/images/carlos-andre.jpg`: cópia da foto para utilização no frontend.
- `docs/requisitos-originais.txt`: pedido integral recebido.

## Leitura da referência

Preservar header compacto, Hero amplo com texto à esquerda e foto à direita, indicadores, quatro projetos, quatro serviços, trajetória em cards, competências, artigos editoriais, vídeos e contato com formulário à esquerda e canais à direita. A seção de contato deve usar paisagem ampla, seguida de CTA azul e rodapé. O mobile deverá reorganizar essas mesmas seções sem suprimir conteúdo.

Paleta inicial: azul-marinho `#07164e`, azul `#0664ff`, azul muito claro `#eef7ff`, violeta `#793cff` e verde `#00b98a`. São tokens iniciais de implementação, sujeitos à comparação visual na Fase 2. Não houve substituição da referência por template nem implementação da página como imagem única.

A fotografia fornecida tem ambiente interno e camiseta clara, diferente do recorte na referência. O original está preservado; o enquadramento do Hero deverá manter a identidade real do proprietário. Não foram geradas fotografias sintéticas.

## Implementação

- Next.js com TypeScript, Tailwind e build standalone, separado da API.
- FastAPI, Pydantic Settings, SQLAlchemy Core e PostgreSQL 16.
- Migração `0001`: 27 tabelas de domínio — as 24 solicitadas e `article_relations`, `video_articles`, `case_images` — além da tabela de controle do Alembic.
- Chaves estrangeiras com `ON DELETE RESTRICT`, índices, unicidade, timestamps e campos editoriais de arquivamento.
- Experiências permitem simultaneidade; datas não são modificadas automaticamente.
- Traduções de artigos têm estado e datas editoriais independentes.
- Cases confidenciais não podem ser marcados como publicados.
- Arquivos são representados por chave, tipo, tamanho, hash e metadados; conteúdo binário fica fora do banco.
- CLI de criação administrativa com Argon2id, confirmação de senha e auditoria, sem credencial padrão.
- Seed idempotente dos quatro projetos em rascunho e categorias de skills.
- Docker Compose e override de desenvolvimento; volumes isolados para banco e mídia; Nginx local.
- `.env.example`, geração local de senha aleatória e instruções de instalação.

## Verificação executada

- Build Next.js no Windows: aprovado, incluindo TypeScript.
- Build Docker do frontend e do backend: aprovado.
- Migração `alembic upgrade head`: executada com sucesso em PostgreSQL 16 real.
- `alembic check`: nenhuma diferença entre modelos e migração.
- Pytest: **15 testes aprovados**. A biblioteca Starlette emitiu um aviso de descontinuação do adaptador httpx do TestClient; não houve falha.
- Seed executado: quatro projetos em rascunho; não publica conteúdo.
- Integridade dos arquivos de referência: hashes iguais aos originais.
- Serviços iniciados: banco e API saudáveis; frontend e Nginx ativos em `127.0.0.1:8080`.
- Requisições pelo Nginx: `/` retornou HTTP 200 e confirmou conexão com a API; `/api/health/ready` retornou banco conectado e migração `0001`.
- Compose com override de desenvolvimento: configuração validada com `config --quiet`; o modo com recarregamento automático não foi iniciado nesta etapa.

## Arquivos criados

`compose.yaml`, `compose.dev.yaml`, `.env.example`, `.gitignore`, `README.md`, `scripts/setup.ps1`; frontend em `frontend/` com Dockerfile, lockfile, configuração TypeScript/PostCSS/Next e tela técnica; backend em `backend/` com Dockerfile, dependências, configuração, modelos, migração, CLI, seed e testes; proxy em `infra/nginx/default.conf`; documentação e referências em `docs/`.

## Pendências

A Home ainda não foi implementada. A tela local é somente uma verificação técnica de comunicação entre frontend, API e banco. Screenshots e comparação de fidelidade visual pertencem à Fase 2 e ainda não foram executados. Não há login, painel, CRUD HTTP, páginas editoriais, API pública de conteúdo ou envio de contato neste estado.

Para o conteúdo real das fases seguintes faltam currículo validado (cargos, períodos, vínculos, formação, certificações e idiomas), PDF do currículo, links sociais e profissionais, URLs reais de vídeos, artigos aprovados, situação real de cada projeto, resultados comprovados, galerias, dados de consultoria e configurações de contato. Os números da imagem de referência não foram tratados como evidência profissional.

Ficam para as respectivas fases: sanitização de HTML, autorização, CSRF, sessões, proteção contra brute force/spam, validação de upload, entrega de e-mail, analytics real, testes Playwright, SEO, TLS, Cloudflare, backups e implantação documentada. Nenhuma publicação externa realizada.
