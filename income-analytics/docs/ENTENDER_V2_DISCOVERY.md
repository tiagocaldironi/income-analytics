# ENTENDER V2 — Discovery

## Current UI

`#entender` hoje começa por um formulário de performance, seguido de risco,
histórico e timeline. A Home já mostra uma versão reduzida da evolução
patrimonial. O frontend usa `performance.js` e `portfolio.js`.

## Current endpoints

- `GET /api/portfolio/performance` entrega TWR, XIRR, fluxos externos e patrimônio.
- `GET /api/portfolio/history` entrega snapshots derivados, agregados por mês ou ano.
- `GET /api/portfolio/dashboard` lê o snapshot persistido da Home.
- `GET /api/portfolio/benchmark-comparison` reutiliza o benchmark configurado.

## Current calculations

`PortfolioProjector` deriva posições, caixa, proventos e patrimônio a partir de
`FinancialEvent` e `MarketPrice`. `PerformanceProjector` calcula TWR e XIRR a
partir dessas mesmas fontes e já neutraliza depósitos e retiradas. Ele será
reutilizado somente para a seção secundária de performance.

## Available historical data

`PortfolioProjector.history` cria `PortfolioSnapshot` para cada data de evento
ou preço persistido. `market_prices` é a fonte histórica de valuation; a leitura
analítica não precisa chamar provedores externos.

## Available cash-flow classification

DEPÓSITO e RETIRADA são fatos explícitos. Operações guardam
`CapitalFlowType` (`EXTERNAL_CAPITAL`, `INTERNAL_TRANSFER`,
`EMPLOYER_CONTRIBUTION`, `UNKNOWN`), mas compra e venda não são tratadas como
aporte ou retirada global. Dividendos, JCP e FII income são eventos estruturados
de renda.

## Current TWR implementation

O TWR está em `PerformanceProjector`; não será duplicado nem usado para
apresentar variação patrimonial.

## Reusable components

`PortfolioSession.portfolio_history`, `PortfolioSession.performance`,
`PortfolioProjector`, `FinancialEffectFactory`, `BaseCurrencyValuationProjector`,
o cliente `portfolioApi`, componentes de tabela e ECharts já existente.

## Problems found and data gaps

Snapshots são derivados em memória a partir de fatos persistidos e o endpoint
atual agrega a série para a Home. Não há ainda uma reconciliação explícita da
mudança patrimonial, contribuição por ativo/classe, nem sinalização estruturada
de cobertura. Valuation ausente impede valorar completamente um snapshot; nesses
casos a explicação deve declarar cobertura parcial ou insuficiente. Eventos de
aluguéis e detalhes de previdência/imóveis não têm, nesta camada, decomposição
econômica completa e não receberão atribuição inventada.

## Proposed reuse/refactor

Criar `WealthExplanationService` de aplicação sobre eventos, preços e snapshots
existentes. Ele calculará tudo em `Decimal`, em moeda-base já refletida nos
snapshots disponíveis, e retornará uma reconciliação, contribuição por classe e
ativo, qualidade de dados e estados para futuros Pontos de Atenção. O endpoint
será uma leitura analítica sem chamadas a provedores de mercado. A tela Entender
consumirá esse endpoint, mantendo TWR como uma seção secundária.
