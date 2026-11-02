# HOME-UX-02 — Hero e trajetória profissional

Branch `codex/home-ux-02`, criada da `main` atualizada em `875b689`, já com as melhorias do PR #3. Implementação e validação locais em 02/11/2026. Sem merge, deploy ou alterações em produção.

## Implementação

O Hero foi separado em um componente de apresentação que recebe os mesmos dados públicos do CMS. Mantém título, texto institucional, CTAs, indicadores, fotografia e assinatura. A fotografia existente `carlos-andre-executivo.png` foi elevada e recebeu enquadramento arredondado por CSS. O arquivo original não foi modificado ou substituído. A assinatura permanece visível também no tablet e no celular.

Os quatro painéis de atuação e a citação formam uma faixa abaixo do conjunto principal. Em 1440px, são cinco colunas com a mesma altura; no tablet, uma grade de duas colunas com a citação ocupando a última linha; no celular, uma sequência vertical. Os painéis usam os ícones, cores e conteúdos existentes.

A trajetória da Home usa os três registros identificados como CAIXA/Compass, RPE.tech/Fiabilité Tech e Alibin, seguidos de um card de outras experiências. Fastconnect aparece primeiro nesse resumo, com cargo e link direto ao vínculo completo. Manager Systems, Cetil, SENAI/SC, Unimed e Someday permanecem no mesmo card, com links individuais.

Os três primeiros cards preservam período, empresa, cargo, descrição, tags, resultados e tecnologias. Resultados e tecnologias podem ser expandidos sem sair da Home. A página completa mantém os nove vínculos e todo o seu conteúdo. Não foram alterados registros, flags de destaque no CMS, datas, cargos ou resultados.

Os componentes novos usam CSS Modules e a escala global de tipografia do PR #3, com leitura a partir de 16px. Os estilos globais antigos exclusivos do Hero e dos cards profissionais foram retirados para evitar regras duplicadas. Não foram adicionadas dependências de produto, fontes remotas ou imagens geradas.

## Comparação com a referência

A [imagem aprovada](references/home-ux-02-aprovado.png) está preservada no repositório. A [comparação lado a lado](screenshots/home-ux-02/comparisons/reference-desktop.png) normaliza apenas a escala da referência para 1440px e mostra a captura real da implementação na mesma largura.

A comparação visual foi usada para corrigir a separação entre assinatura e foto, elevar a fotografia, ajustar a distribuição das duas colunas e refinar largura e espaçamento dos cinco painéis. A imagem de referência não foi usada como fundo da página: a implementação utiliza elementos HTML acessíveis e a fotografia já existente.

Diferenças deliberadamente preservadas: o cabeçalho e as demais seções continuam com o conteúdo existente, incluindo os textos mais completos e a tipografia acessível do PR #3. O enquadramento se adapta ao retrato original; a escrita manuscrita usa as fontes já configuradas no projeto e pode variar entre sistemas operacionais. A aprovação visual e a homologação funcional permanecem pendentes do responsável pelo portfólio antes de qualquer publicação.

## Testes executados

| Verificação | Resultado |
| --- | --- |
| Build de produção Next.js | Passou, incluindo TypeScript |
| `pnpm typecheck` separado | Passou |
| `home-article-order.spec.cjs` | Passou: quatro artigos, ordem e demais módulos preservados |
| `typography-tokens.spec.cjs` | Passou: tokens definidos e contrastes principais AA |
| `api-errors.spec.cjs` | Passou: 11 casos de resposta/CSRF existentes |
| Navegador real | Passou em 1440, 768 e 390px |
| Zoom nativo | Passou em 100%, 125%, 150% e 200% no desktop |
| Layout | Cinco painéis alinhados e com alturas iguais; trajetória em quatro/duas/uma coluna |
| Tipografia | Nenhum texto visível abaixo de 16px; sem overflow horizontal nas larguras e zooms testados |
| Navegação | CTAs, menu móvel, teclado, link da trajetória e âncora de Fastconnect passaram |
| CMS | Login e listagem de Artigos passaram, sem edição ou publicação |
| Dados profissionais | Texto integral dos nove vínculos idêntico ao baseline em todas as resoluções |
| Fotografia | Bytes idênticos aos da `main`; hash registrado no relatório |
| Regressão | 24 comparações das seções preservadas da Home, mais SmartFamily, AVALLOW e Beloria, passaram |

O [relatório do navegador](screenshots/home-ux-02/after/report.json) registra 15 verificações de layout: três medições das grades e 12 combinações de página/resolução/zoom, além de 29 registros de regressão e preservação. O zoom foi aplicado por `chrome.tabs.setZoom` e validado pelo `devicePixelRatio`; não se trata de zoom CSS ou de redimensionamento de uma captura.

As comparações de regressão consideram conteúdo visível, imagens, links, tipografia, cores e dimensões. Desconsideram a mudança esperada na posição vertical das seções abaixo do Hero e os scripts internos com hashes diferentes entre builds. Os snapshots públicos da API permaneceram iguais durante os testes. Backend e dados não foram modificados neste PR; não foi repetida a suíte de backend, pois a alteração é de apresentação.

## Capturas reais antes/depois

| Região | Desktop 1440px | Tablet 768px | Celular 390px |
| --- | --- | --- | --- |
| Home completa | [comparar](screenshots/home-ux-02/comparisons/home-1440.png) | [comparar](screenshots/home-ux-02/comparisons/home-768.png) | [comparar](screenshots/home-ux-02/comparisons/home-390.png) |
| Hero | [comparar](screenshots/home-ux-02/comparisons/hero-1440.png) | [comparar](screenshots/home-ux-02/comparisons/hero-768.png) | [comparar](screenshots/home-ux-02/comparisons/hero-390.png) |
| Trajetória da Home | [comparar](screenshots/home-ux-02/comparisons/trajectory-1440.png) | [comparar](screenshots/home-ux-02/comparisons/trajectory-768.png) | [comparar](screenshots/home-ux-02/comparisons/trajectory-390.png) |

Capturas completas, sem redução, ficam em `screenshots/home-ux-02/before` e `after`, incluindo a página completa de experiência. Os arquivos `home-zoom-*.png` e `experience-zoom-*.png` documentam os quatro níveis de zoom. As comparações de Home completa são miniaturas lado a lado para revisão; os originais completos permanecem disponíveis.

## Arquivos e execução local

- `frontend/src/components/home/hero.tsx`: composição do Hero, fotografia, assinatura e painéis.
- `frontend/src/components/home/trajectory.tsx`: quatro cards, detalhes e links aos vínculos existentes.
- `frontend/src/components/home/intro.module.css`: layout, tipografia, enquadramento e breakpoints desses componentes.
- `frontend/src/app/page.tsx` e `globals.css`: integração e retirada das regras substituídas.
- `frontend/tests/home-ux-02.spec.cjs`: teste real de navegador, snapshots e regressões.
- `scripts/verify-home-ux.py` e `compare-home-ux.cjs`: ambiente descartável e montagem das evidências.

Requer Docker, Python, Node e ferramentas de QA Playwright/Sharp disponíveis no ambiente. Não foram adicionadas ao pacote de produção. Configure `NODE_PATH` ou `PLAYWRIGHT_MODULE`/`SHARP_MODULE` quando necessário; `QA_CHROME` permite selecionar um navegador compatível com extensões para o zoom nativo.

```powershell
docker build -t portfolio-home-ux-backend ./backend
docker build -t portfolio-home-ux-after ./frontend
python scripts/verify-home-ux.py setup
node frontend/tests/home-ux-02.spec.cjs before
python scripts/verify-home-ux.py after
node frontend/tests/home-ux-02.spec.cjs after
node frontend/tests/home-article-order.spec.cjs
node frontend/tests/typography-tokens.spec.cjs
node frontend/tests/api-errors.spec.cjs
node scripts/compare-home-ux.cjs
python scripts/verify-home-ux.py cleanup
```

O helper lê o PostgreSQL e a mídia do ambiente local existente e restaura cópias em rede, containers e volumes próprios, com prefixo `portfolio-home-ux-02-qa`, acessíveis apenas por loopback na porta 8098. O código anterior é extraído de `875b689`, sem reset do workspace. A migração já existente é aplicada somente à cópia. Credenciais temporárias ficam em `.private`, ignorado pelo Git, e são retiradas no cleanup. O ambiente local original e produção são preservados.
