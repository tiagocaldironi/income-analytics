# Minha Carteira V2: auditoria e contrato de apresentação

Base: develop 39ccc81, Firebase e ownership preservados. Trabalho em worktree separada do processo oficial. Não usar banco pessoal nem reiniciar o serviço real.

| Região | Fonte existente | Semântica preservada |
|---|---|---|
| Patrimônio atual | dashboard.portfolio.total_market_value | Valor de mercado; null significa valuation parcial |
| Rentabilidade 12 meses | dashboard.performance | TWR; cobertura/indisponibilidade preservadas |
| Rendimentos recebidos | dashboard.portfolio.income_received | Acumulado, sem confundir com valorização |
| Capital aplicado | capital_applied/status/partial_amount | Custo das posições atuais; não capital líquido investido |
| Evolução | dashboard.history e history(period,class) | Custo + resultado econômico, não TWR |
| Composição | holdings.classes / market_value | Moeda-base; classes sem valuation e saldos negativos continuam explícitos |
| Comparação | performanceComparison | TWR e benchmarks com tipos distintos e estados independentes |
| Rendimentos mensais | operations, grupo INCOME | Data de recebimento, separado por moeda |
| Meus ativos | dashboard.holdings | Classes, contratos, quantidade, PM, cotação, saldo, resultado, variação, renda, pesos e ações |

Tabelas reutilizam assetsForDisplay/renderHoldingRow e menus atuais: lançamentos paginados, compras/vendas, distribuição do grupo e editor de alocação. Nova apresentação não muda agrupamento nem cálculos. Charts ECharts SVG, ResizeObserver já existente na evolução/performance; painel de rendimentos exige resize ao tornar visível. Filtros são DOM persistente entre abas; navegação não chama endpoints.

Compartilhados: cabeçalho, seletor de carteiras autorizadas, navegação, shared/ui.js, charts.js, account-menu. Temas atuais usam --ia-* e data-theme por carteira. V2 adiciona --income-* sem remover tokens legados. Ícones SVG locais, sem nova biblioteca. Onboarding de apresentação será metadado separado por usuário/carteira; a jornada educacional de reserva existente permanece independente.

Entrega em quatro PRs empilhados: tokens/componentes; shell/cabeçalho/indicadores/análises; ativos responsivos; orientação/persistência. Nenhum merge automático. Evidências apenas com dados identificados de teste em SQLite descartável, incluindo carteira vazia.
