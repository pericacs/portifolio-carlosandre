# Fase 2 — implementação para validação local

Entrega em 14/10/2026. Validação: http://localhost:8080/.

A tela provisória foi substituída pela Home real. A implementação usa a composição de `references/portfolio-aprovado.png`, a fotografia original e o currículo indicado pelo proprietário. As páginas `/experiencia`, `/sobre` e `/cases` também estão disponíveis.

## Conteúdo e apresentação

- Header e menu mobile, hero, indicadores, quatro projetos, quatro serviços, trajetória, sete áreas de competências, artigos, vídeos, contato e footer.
- Nove experiências, nove cases e sete grupos de competências extraídos do DOCX. A trajetória completa tem detalhes expansíveis; os cards da Home priorizam CEF, RPE.tech, Alibin e Fastconnect.
- A data final da Compass UOL permanece em validação. Não foi presumido vínculo atual. Os períodos simultâneos foram preservados.
- Resultados quantitativos são declarações do currículo fornecido, sem alegação de auditoria independente.
- O original está preservado em `private/curriculo-original.docx`, fora do diretório público e ignorado pelo controle de versão. O download público usa uma cópia sem endereço residencial, com metadados pessoais removidos e a data da Compass corrigida para validação.
- Conteúdo estruturado em `frontend/src/data/curriculum.json`, com regras para integração futura documentadas em `admin-content-contract.md`.

## Comparação visual

Foi feita inspeção visual das capturas reais, comparando a sequência, cores, composição e cartões com a referência aprovada. O hero mantém texto à esquerda e fotografia à direita; os quatro projetos e serviços, o primeiro cartão de experiência azul, artigos e vídeos, contato em duas colunas e footer seguem a composição aprovada. A fotografia é a original, sem substituição gerada.

As ilustrações dos cards são recortes da referência, usados apenas como imagens: títulos, conteúdo, botões e formulários são HTML real. A resolução da referência limita a nitidez desses recortes. As sete áreas de competências solicitadas ocupam duas linhas no desktop, e o conteúdo do currículo amplia naturalmente a página. Não há altura fixa para a página. Miniaturas mantêm suas proporções; o mobile reorganiza os cartões e o formulário sem rolagem horizontal.

## Verificações executadas

- Build local Next.js/TypeScript e build Docker do frontend concluídos.
- Playwright em 1440, 768 e 390 px: título e seções, ausência da tela provisória, imagens carregadas, proporções, ausência de overflow horizontal e de erros JavaScript.
- Menu mobile, modais, Escape e retorno de foco, validação do formulário e preparação do link de e-mail.
- Rotas Home, experiência, sobre e cases com HTTP 200; nove itens na trajetória e detalhes expansíveis; aviso da Compass; download DOCX válido.
- API e banco saudáveis. Somente o container frontend foi reconstruído; backend, banco e Nginx foram preservados.
- Verificação de privacidade, integridade do original e conteúdo normalizado: nove experiências, nove cases e sete áreas.
- A cópia pública do DOCX foi renderizada em 20 páginas e todas foram inspecionadas. Foram corrigidos marcadores de lista incompatíveis e a página afetada foi renderizada e inspecionada novamente.

Evidências em `screenshots/`: `home-1440.png`, `home-390.png`, `home-768.png`, capturas das páginas adicionais e dos trechos mobile, `playwright-report.json` e `content-validation.json`. A Home tem altura natural de 3623 px no desktop e 9650 px em 390 px.

Para repetir os testes, disponibilize Playwright no Node (ou indique seu módulo pela variável `PLAYWRIGHT_MODULE`) e execute `node frontend/tests/home.spec.cjs` a partir da raiz. A validação de conteúdo usa `python scripts/validate-phase2.py` com o original privado presente. Para atualizar somente o frontend: `docker compose up -d --no-deps --build frontend`.

## Arquivos criados ou alterados nesta etapa

- `frontend/src/app/page.tsx`, `globals.css`, `layout.tsx`, `icon.svg`: Home, identidade visual e responsividade.
- `frontend/src/app/experiencia/page.tsx`, `sobre/page.tsx`, `cases/page.tsx`: currículo e cases.
- `frontend/src/components/artwork.tsx`, `icon.tsx`, `home-interactions.tsx`: imagens, ícones e interações.
- `frontend/src/data/home.ts`, `curriculum.json`, `contact.ts`: conteúdo separado da apresentação.
- `frontend/public/images/`: fotografia e referência visual; `frontend/public/documents/carlos-andre-curriculo-publico.docx`: download público.
- `frontend/tests/home.spec.cjs`, `capture.cjs`: testes e capturas reais.
- `scripts/read-cv.py`, `prepare-curriculum.py`, `prepare-public-resume.py`, `validate-phase2.py`: extração, normalização e validação.
- `.gitignore`, `README.md`, documentação e evidências desta fase. Os materiais privados e de renderização permanecem em `docs/private/`.

## Pendências explícitas

Artigos e vídeos estão identificados como conteúdos em preparação; não foram inventados links, durações ou publicações. LinkedIn, YouTube e agenda aguardam URLs confirmadas. O formulário prepara uma mensagem no aplicativo de e-mail e não simula envio por uma API.

O painel `/admin`, a edição persistida e a substituição de currículo pelo painel pertencem à próxima fase. Nesta entrega, o conteúdo está estruturado para essa integração, que ainda não está funcional. Não houve publicação externa; o ambiente continua local e com indexação desativada.
