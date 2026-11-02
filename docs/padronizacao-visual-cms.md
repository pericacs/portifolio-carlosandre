# Padronização visual, tipografia e exclusividade editorial

Validação local em 02/11/2026. Branch `codex/visual-cms-accessibility`, baseada em `main` (`7c1aa6b`). Nenhum merge, deploy, acesso SSH ou escrita em produção foi realizado.

## Comportamento entregue

- Home e Artigos usam o mesmo `ArticleCard`, `ArticleCover` e `ArticleTags`. A moldura é sempre 16:9 e a imagem usa `object-fit: contain`, preservando todas as bordas e os textos da arte, sem distorção. O CMS permite alinhar a imagem inteira ao centro, topo, base, esquerda ou direita na aba Mídia. Os arquivos originais não foram alterados.
- Títulos e resumos dos cards não são truncados por quantidade de linhas. Os cards se estendem à mesma altura em cada linha; a Home mantém a grade de quatro, duas e uma coluna.
- O armazenamento efetivamente usado pelo CMS é `cms_entries.data.tags` (rascunho), `published_data.tags` (publicado) e `scheduled_data.tags` (agendado), em arrays JSONB. A tabela relacional antiga `article_tags` não é a fonte desse fluxo. Os artigos continuam com seus dados existentes; nenhum preenchimento fictício foi aplicado.
- Tags passaram para Informações gerais, com sugestões das tags cadastradas e inclusão de novos nomes. Unicode, espaços, maiúsculas e acentos são normalizados para deduplicação. O primeiro nome cadastrado é reutilizado; a grafia não precisa perder os acentos. Home, listagem e leitura usam as tags cadastradas, sem substituí-las pelas categorias.
- Cada marcação (`featured`, Marcação editorial; `spotlight`, Destaque principal) pode pertencer a apenas uma publicação. Publicar transfere somente as opções selecionadas. Uma publicação com ambas transfere ambas. Salvar, restaurar ou agendar rascunhos não remove os destaques públicos.
- O CMS informa os títulos que serão substituídos. A decisão definitiva ocorre na transação de publicação; sessões com versões anteriores recebem conflito ao tentar sobrescrever um artigo modificado pela transferência.
- Despublicar, arquivar ou excluir continua retirando o snapshot público. Não há uma referência externa ao artigo destacado que possa ficar inválida. Publicações invisíveis ou em preparação não tomam os destaques públicos.
- A Home preserva a política já integrada à `main`: os quatro artigos publicados elegíveis mais recentes, ou todos os disponíveis quando existem menos de quatro. A API determina a ordem por data editorial/primeira publicação antes do limite. Marcações e ordem manual não alteram essa sequência. Artigos mantém a mesma sequência na grade; o painel de destaque é uma apresentação adicional.

## Atomicidade e migração

O advisory lock transacional PostgreSQL `(73194, 1)` é obtido antes dos locks dos artigos, inclusive no worker. Retirada das marcações anteriores, nova publicação, versões, referências e auditoria ficam na mesma transação. Dois índices únicos parciais também impedem duplicação por escritas que não usem o fluxo da aplicação.

A migração `0004` reconcilia marcações antigas duplicadas de maneira determinística, mantendo a publicação mais recente elegível como titular de cada opção. Ajusta apenas os metadados das marcações nos snapshots necessários; preserva conteúdo, publicação, datas, artigos e revisões anteriores. Registra a ação `editorial_reconciled`, incluindo o snapshot público anterior no histórico. A migração foi aplicada somente aos bancos descartáveis. O downgrade retira os índices, sem reintroduzir duplicações nem apagar histórico.

Uma transferência normal registra `editorial_replaced`, mantém a publicação anterior e sua data original, preserva edições pendentes e incrementa a versão do artigo substituído. Se qualquer etapa falhar, o rollback conserva os dois artigos no estado anterior.

## Observações internas e dados profissionais

Foi removida da Home a observação solicitada sobre resultados, Compass UOL e vínculos simultâneos. A investigação encontrou também notas de revisão no início da trajetória, um badge sobre confirmação do vínculo, o sufixo visual “término em validação” e um aviso de confirmação pelo proprietário nos detalhes dos projetos. Essas apresentações foram retiradas.

Datas, cargos, resultados, vínculos e arquivos de currículo não foram editados. O indicador de revisão permanece nos dados e no CMS; no público, um período sem data final cadastrada mostra a data de início, sem inventar um término ou declarar um vínculo atual. Referências públicas de fonte dos cases e avisos funcionais de conteúdo em preparação foram preservados.

## Tipografia e acessibilidade

Todos os estilos públicos, SmartFamily e administrativos usam a escala global em `rem`, com mínimo de 1rem/16px para textos visíveis. Títulos fluidos também usam os tokens. Textos de leitura usam entrelinha confortável, com token principal 1.6. Menus, botões, metadados, datas, tags, placeholders e formulários foram ampliados; cards, cabeçalho, colunas, navegação e campos acomodam a expansão.

Foram reforçados os tons de texto, chamadas e placeholders, preservando azul, fundos claros e a identidade visual. Os pares principais de leitura foram medidos pelo cálculo de luminância WCAG: texto secundário/branco 7,02:1; azul/branco 6,18:1; placeholder/campo 5,89:1; texto administrativo/fundo 6,55:1; tags 8,17:1. Isso não constitui uma certificação integral WCAG de imagens, serviços externos ou conteúdo futuro.

## Verificações executadas

| Verificação | Resultado |
| --- | --- |
| Build Next.js, com TypeScript | Passou |
| `pnpm typecheck` separado | Passou |
| `alembic upgrade head` e `alembic check` | Passaram; sem diferenças pendentes |
| Suíte completa de backend | **135 passaram, 20 ignorados**, 1 aviso de depreciação existente |
| Matriz de páginas e zoom nativo | **53 páginas, 318 combinações**, sem overflow horizontal ou texto visível abaixo de 16px |
| Abas do CMS | **288 combinações** de aba/largura, incluindo SmartFamily |
| Cinco artigos temporários | Home com quatro, ordem cronológica, linhas alinhadas, sem tags inventadas |
| Fluxo CMS | Tags criadas, deduplicadas, salvas e recarregadas; enquadramento persistido; ambos os títulos de substituição exibidos; rascunho preserva destaques públicos |
| Capas reais | 16:9, imagens carregadas e inteiras com `contain` em 1440, 768 e 390px |
| Atomicidade | Transferência independente/conjunta, rollback por falha, índices únicos, disputa entre publicações e entre publicação/worker |
| Preservação | Artigos, conteúdo, datas de publicação, rascunhos pendentes e histórico; reconciliação de dados legados testada |

Os 20 testes ignorados dependem de dois documentos Word privados e de um pacote editorial privado com 18 casos, não fornecidos a essa execução. Os testes novos de concorrência, exclusividade e migração foram executados com PostgreSQL real.

O zoom foi alterado pela API nativa `chrome.tabs.setZoom` em um perfil descartável do Edge. A automação conferiu `devicePixelRatio` 1, 1.25, 1.5 e 2; a 200%, o viewport CSS de uma janela de 1440px passou a 720px. Não foi usado apenas redimensionamento de imagem ou zoom CSS como substituto. Também houve validação direta das larguras 768 e 390px.

## Evidências

Os arquivos em `screenshots/visual-cms/before` e `after` são capturas reais de página inteira. As comparações abaixo mostram o início de cada captura lado a lado; os originais completos permanecem disponíveis.

| Página | 1440px | 768px | 390px |
| --- | --- | --- | --- |
| Home antes/depois | [comparar](screenshots/visual-cms/comparisons/home-1440.png) | [comparar](screenshots/visual-cms/comparisons/home-768.png) | [comparar](screenshots/visual-cms/comparisons/home-390.png) |
| Artigos antes/depois | [comparar](screenshots/visual-cms/comparisons/artigos-1440.png) | [comparar](screenshots/visual-cms/comparisons/artigos-768.png) | [comparar](screenshots/visual-cms/comparisons/artigos-390.png) |
| CMS antes/depois | [comparar](screenshots/visual-cms/comparisons/cms-1440.png) | [comparar](screenshots/visual-cms/comparisons/cms-768.png) | [comparar](screenshots/visual-cms/comparisons/cms-390.png) |

Capturas finais: [Home](screenshots/visual-cms/after/home-1440.png), [Artigos](screenshots/visual-cms/after/artigos-1440.png), [CMS](screenshots/visual-cms/after/cms-1440.png), [Publicação](screenshots/visual-cms/after/cms-publicacao-390.png), [enquadramento](screenshots/visual-cms/after/cms-media-390.png). Há capturas adicionais das três telas a 100%, 125%, 150% e 200%, com nomes `*-zoom-*.png`.

Relatórios: [matriz completa](screenshots/visual-cms/after/report.json), [capturas do build final](screenshots/visual-cms/after/capture-report.json), [abas](screenshots/visual-cms/cms-tabs-report.json), [quatro artigos e CMS](screenshots/visual-cms/four-articles-report.json), [tipografia e contraste](screenshots/visual-cms/typography-report.json).

**Limite da referência:** a cópia local contém dois artigos publicados sobre Split Payment e não contém o artigo da Binance. As capturas mantêm esses dois artigos reais; não foram preenchidas com conteúdo fictício. O comportamento com quatro artigos foi provado separadamente com cinco registros temporários, criados e retirados apenas na cópia descartável. A preservação integral das capas é garantida pelo componente compartilhado e testada com as imagens reais disponíveis; a comparação específica da arte da Binance permanece dependente desse conteúdo.

## Reproduzir localmente

Requer Docker, Node, Python, Playwright e Sharp. O ambiente original local precisa estar ativo para a cópia somente de leitura. Use `PLAYWRIGHT_MODULE`, `SHARP_MODULE`, `NODE_PATH` e `QA_CHROME` quando os módulos ou o navegador não estiverem nos caminhos padrão.

```powershell
docker build -t portfolio-visual-backend ./backend
docker build -t portfolio-visual-after ./frontend
python scripts/verify-visual-cms.py setup
node frontend/tests/visual-cms.spec.cjs before
python scripts/verify-visual-cms.py after
python scripts/verify-visual-cms.py test
node frontend/tests/visual-cms.spec.cjs after
node frontend/tests/cms-tabs.spec.cjs
node frontend/tests/article-home-four.spec.cjs
node frontend/tests/typography-tokens.spec.cjs
node scripts/compare-visual-cms.cjs
python scripts/verify-visual-cms.py cleanup
```

O helper usa rede, volumes e containers exclusivos com prefixo `portfolio-visual-cms-qa`, porta loopback 8097 e um segundo banco `portfolio_tests`. O baseline de código é extraído de `7c1aa6b`, sem checkout ou reset do workspace. Credenciais aleatórias de QA ficam somente em `.private`, ignorado pelo Git, e são retiradas no cleanup. Nenhum teste deve ser apontado para produção.
