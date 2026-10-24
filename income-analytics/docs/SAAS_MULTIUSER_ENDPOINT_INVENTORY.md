# Inventário de endpoints — SaaS Multiusuário, Fase 1

Coleta AST do workspace em 23/10/2026: **96 rotas explícitas** (92 sob `/api`, dois aliases `/imports/b3`, `/` e `/health`). Inclui as rotas de atualização assíncrona do dashboard implementadas no workspace. Adicionalmente, FastAPI expõe `/docs`, `/redoc`, `/openapi.json` e o mount `/static`; esses não são decoradores financeiros e exigem política de implantação própria.

Nenhuma das 96 declarações possui `Depends`/`Security` de autenticação. A análise manual de `main.py` também confirma que o middleware valida carteira/estado, não usuário. **Todas as operações privadas listadas estão acessíveis sem login a quem alcança a aplicação e conhece/descobre a carteira.** As verificações de carteira, validações de negócio e estados DRAFT/PUBLISHED continuam existindo; isso não é autenticação.

A última coluna é a política proposta, não proteção já instalada. Rotas de referência podem compartilhar armazenamento/cache sem que isso autorize escrita global por um usuário comum. A licença do provedor pode exigir leitura autenticada mesmo para dados de mercado.

| Método | Rota | Handler / evidência | Gate SaaS necessário |
|---|---|---|---|
| GET | `/` | `dashboard` — [main.py:174](../src/income_analytics/main.py) | Público mínimo (shell/health); sem dados financeiros |
| PUT | `/api/allocation-policy` | `set_allocation_policy` — [dashboard.py:4276](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/analytics/performance-comparison` | `get_performance_comparison` — [dashboard.py:3911](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/analytics/wealth-evolution` | `get_wealth_evolution` — [dashboard.py:3769](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/analytics/wealth-explanation` | `get_wealth_explanation` — [dashboard.py:3716](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| PUT | `/api/asset-allocation-policy` | `set_asset_allocation_policy` — [dashboard.py:4289](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/assets` | `create_asset` — [dashboard.py:883](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/assets/fixed-income` | `create_fixed_income_asset` — [dashboard.py:896](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/assets/pension-plans` | `create_pension_plan` — [dashboard.py:943](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/assets/real-estate` | `create_real_estate` — [dashboard.py:1055](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/assets/search` | `search_assets` — [dashboard.py:825](../src/income_analytics/api/routers/dashboard.py) | Descoberta de referência; autenticar e limitar custo do provedor |
| PUT | `/api/assets/{ticker}/class` | `update_asset_class` — [dashboard.py:4160](../src/income_analytics/api/routers/dashboard.py) | Proprietário + override privado/curadoria; não alterar catálogo global |
| GET | `/api/benchmarks/{name}` | `get_benchmark_observations` — [dashboard.py:4060](../src/income_analytics/api/routers/dashboard.py) | Referência compartilhável; leitura licenciada |
| POST | `/api/benchmarks/{name}` | `create_benchmark_rate` — [dashboard.py:3956](../src/income_analytics/api/routers/dashboard.py) | Ingestão de referência por serviço; negar escrita global ao usuário |
| POST | `/api/benchmarks/{name}/refresh` | `refresh_benchmark` — [dashboard.py:3971](../src/income_analytics/api/routers/dashboard.py) | Ingestão de referência por serviço; negar escrita global ao usuário |
| GET | `/api/data-sources` | `get_data_sources` — [dashboard.py:3998](../src/income_analytics/api/routers/dashboard.py) | Operacional; filtrar mensagens e não revelar atividade de titulares |
| POST | `/api/data/reset` | `reset_all_data` — [dashboard.py:4633](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/dividends` | `create_dividend` — [dashboard.py:3565](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/external-flows` | `create_external_flow` — [dashboard.py:3626](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/fii-income` | `create_fii_income` — [dashboard.py:3608](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/fixed-income/sales` | `create_fixed_income_sale` — [dashboard.py:2353](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/fx-rates/history/backfill` | `backfill_fx_rate_history` — [dashboard.py:3455](../src/income_analytics/api/routers/dashboard.py) | Ingestão de referência por serviço; negar escrita global ao usuário |
| POST | `/api/fx/{base_currency}/{quote_currency}/refresh` | `refresh_fx_rate` — [dashboard.py:2299](../src/income_analytics/api/routers/dashboard.py) | Ingestão de referência por serviço; negar escrita global ao usuário |
| GET | `/api/imports/b3/history` | `list_b3_import_history` — [dashboard.py:2593](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/imports/b3/preview` | `preview_b3_import` — [dashboard.py:2627](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/imports/b3/{batch_id}/apply` | `apply_b3_import` — [dashboard.py:2665](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/imports/irpf/brazilian-stocks` | `import_irpf_brazilian_stocks` — [dashboard.py:2454](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/imports/irpf/brazilian-stocks/preview` | `preview_irpf_brazilian_stocks_import` — [dashboard.py:2440](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/income-starter/active-strategy` | `get_active_strategy_metadata` — [income_starter.py:57](../src/income_analytics/api/routers/income_starter.py) | Privado; proprietário da carteira e gate editorial na adoção |
| GET | `/api/income-starter/catalog` | `list_income_starter_models` — [income_starter.py:33](../src/income_analytics/api/routers/income_starter.py) | Referência/editorial; público só PUBLISHED licenciado; DRAFT restrito ao fluxo autorizado |
| GET | `/api/income-starter/journey/reserve` | `get_reserve_journey_progress` — [income_starter.py:38](../src/income_analytics/api/routers/income_starter.py) | Privado; proprietário da carteira e gate editorial na adoção |
| PUT | `/api/income-starter/journey/reserve` | `save_reserve_journey_progress` — [income_starter.py:43](../src/income_analytics/api/routers/income_starter.py) | Privado; proprietário da carteira e gate editorial na adoção |
| GET | `/api/income-starter/models/{template_key}` | `get_income_starter_model` — [income_starter.py:62](../src/income_analytics/api/routers/income_starter.py) | Referência/editorial; público só PUBLISHED licenciado; DRAFT restrito ao fluxo autorizado |
| POST | `/api/income-starter/models/{template_key}/adopt` | `adopt_income_starter_model` — [income_starter.py:70](../src/income_analytics/api/routers/income_starter.py) | Privado; proprietário da carteira e gate editorial na adoção |
| POST | `/api/jcp` | `create_jcp` — [dashboard.py:3585](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/market-prices/crypto/history/backfill` | `backfill_crypto_market_price_history` — [dashboard.py:3530](../src/income_analytics/api/routers/dashboard.py) | Proprietário quando usa carteira + serviço de mercado/quota |
| POST | `/api/market-prices/historical-cache/refresh` | `refresh_historical_price_cache` — [dashboard.py:3305](../src/income_analytics/api/routers/dashboard.py) | Proprietário quando usa carteira + serviço de mercado/quota |
| POST | `/api/market-prices/history/b3-etf/backfill` | `backfill_b3_etf_price_history` — [dashboard.py:3318](../src/income_analytics/api/routers/dashboard.py) | Proprietário quando usa carteira + serviço de mercado/quota |
| POST | `/api/market-prices/history/backfill` | `backfill_market_price_history` — [dashboard.py:3377](../src/income_analytics/api/routers/dashboard.py) | Proprietário quando usa carteira + serviço de mercado/quota |
| POST | `/api/market-prices/refresh` | `refresh_market_prices` — [dashboard.py:2808](../src/income_analytics/api/routers/dashboard.py) | Proprietário quando usa carteira + serviço de mercado/quota |
| GET | `/api/market-prices/refresh-runs` | `list_market_price_refresh_runs` — [dashboard.py:2803](../src/income_analytics/api/routers/dashboard.py) | Privado; logs da carteira e autorização do proprietário |
| POST | `/api/market-prices/us/history/backfill` | `backfill_us_market_price_history` — [dashboard.py:3490](../src/income_analytics/api/routers/dashboard.py) | Proprietário quando usa carteira + serviço de mercado/quota |
| PUT | `/api/market-prices/{ticker}` | `update_market_price` — [dashboard.py:2782](../src/income_analytics/api/routers/dashboard.py) | Proprietário + override privado; bloquear mutação canônica global |
| GET | `/api/market-prices/{ticker}/automatic` | `get_automatic_market_price` — [dashboard.py:3260](../src/income_analytics/api/routers/dashboard.py) | Proprietário quando usa carteira + serviço de mercado/quota |
| GET | `/api/operations` | `get_operations` — [dashboard.py:1849](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/operations/history` | `get_operations_history` — [dashboard.py:1873](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| DELETE | `/api/operations/{event_id}` | `delete_operation` — [dashboard.py:2211](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/pensions/{ticker}/fund-return` | `pension_fund_return` — [dashboard.py:1013](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| PUT | `/api/pensions/{ticker}/vehicle` | `associate_pension_vehicle` — [dashboard.py:957](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/pensions/{ticker}/vehicle/refresh` | `refresh_pension_vehicle` — [dashboard.py:984](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio` | `get_portfolio` — [dashboard.py:1265](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/allocation` | `get_portfolio_allocation` — [dashboard.py:4132](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/allocation-analysis` | `get_allocation_analysis` — [dashboard.py:4301](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/assets/{asset_id}/transactions` | `get_asset_transactions` — [dashboard.py:1734](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/benchmark-comparison` | `get_benchmark_comparison` — [dashboard.py:3939](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/class-allocation` | `get_portfolio_class_allocation` — [dashboard.py:4172](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/configuration` | `get_portfolio_configuration` — [dashboard.py:2220](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| PUT | `/api/portfolio/configuration` | `update_portfolio_configuration` — [dashboard.py:2225](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/dashboard` | `get_portfolio_dashboard` — [dashboard.py:1424](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/portfolio/dashboard/rebuild` | `rebuild_portfolio_dashboard` — [dashboard.py:1436](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/portfolio/dashboard/refresh` | `request_dashboard_refresh` — [dashboard.py:1346](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/dashboard/refresh-status` | `get_dashboard_refresh_status` — [dashboard.py:1332](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/diversification` | `get_portfolio_diversification` — [dashboard.py:4214](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/history` | `get_portfolio_history` — [dashboard.py:4513](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/holdings` | `get_portfolio_holdings` — [dashboard.py:1448](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/intelligence` | `get_portfolio_intelligence` — [dashboard.py:4235](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/performance` | `get_portfolio_performance` — [dashboard.py:3646](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/rebalancing` | `get_rebalancing` — [dashboard.py:4326](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/portfolio/rebalancing/assets` | `simulate_asset_rebalancing` — [dashboard.py:4497](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/portfolio/rebalancing/contribution-only` | `simulate_contribution_rebalancing` — [dashboard.py:4350](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/risk` | `get_portfolio_risk` — [dashboard.py:4087](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolio/risk-contribution` | `get_portfolio_risk_contribution` — [dashboard.py:4111](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/portfolio/simulation/contribution` | `project_hypothetical_contribution` — [dashboard.py:4370](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/portfolios` | `list_portfolios` — [portfolios.py:85](../src/income_analytics/api/routers/portfolios.py) | Autenticado; lista por usuário e proprietário de cada ID |
| POST | `/api/portfolios` | `create_portfolio` — [portfolios.py:90](../src/income_analytics/api/routers/portfolios.py) | Autenticado; lista por usuário e proprietário de cada ID |
| PATCH | `/api/portfolios/{portfolio_id}` | `rename_portfolio` — [portfolios.py:112](../src/income_analytics/api/routers/portfolios.py) | Autenticado; lista por usuário e proprietário de cada ID |
| POST | `/api/portfolios/{portfolio_id}/archive` | `archive_portfolio` — [portfolios.py:165](../src/income_analytics/api/routers/portfolios.py) | Autenticado; lista por usuário e proprietário de cada ID |
| POST | `/api/portfolios/{portfolio_id}/restore` | `restore_portfolio` — [portfolios.py:170](../src/income_analytics/api/routers/portfolios.py) | Autenticado; lista por usuário e proprietário de cada ID |
| GET | `/api/recurring-rules` | `list_recurring_rules` — [dashboard.py:1155](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/recurring-rules` | `create_recurring_rule` — [dashboard.py:1069](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/recurring-rules/execute` | `execute_recurring_rules` — [dashboard.py:1100](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| DELETE | `/api/recurring-rules/{rule_id}` | `delete_recurring_rule` — [dashboard.py:1147](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| PUT | `/api/recurring-rules/{rule_id}` | `update_recurring_rule` — [dashboard.py:1106](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| POST | `/api/recurring-rules/{rule_id}/close` | `close_recurring_rule` — [dashboard.py:1130](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/api/settings/paid-income` | `get_paid_income_settings` — [dashboard.py:2249](../src/income_analytics/api/routers/dashboard.py) | Operação global sensível; serviço/admin ou redesenho por titular |
| PUT | `/api/settings/paid-income` | `update_paid_income_settings` — [dashboard.py:2254](../src/income_analytics/api/routers/dashboard.py) | Operação global sensível; serviço/admin ou redesenho por titular |
| POST | `/api/settings/paid-income/sync` | `sync_paid_income` — [dashboard.py:2283](../src/income_analytics/api/routers/dashboard.py) | Operação global sensível; serviço/admin ou redesenho por titular |
| POST | `/api/settings/paid-income/test` | `test_paid_income_connection` — [dashboard.py:2272](../src/income_analytics/api/routers/dashboard.py) | Operação global sensível; serviço/admin ou redesenho por titular |
| GET | `/api/tools` | `list_investment_tools` — [dashboard.py:601](../src/income_analytics/api/routers/dashboard.py) | Referência compartilhável; licença, quota e gate de leitura |
| GET | `/api/tools/magic-formula/fiis` | `magic_formula_fiis` — [dashboard.py:820](../src/income_analytics/api/routers/dashboard.py) | Referência compartilhável; licença, quota e gate de leitura |
| GET | `/api/tools/magic-formula/stocks` | `magic_formula_stocks` — [dashboard.py:614](../src/income_analytics/api/routers/dashboard.py) | Referência compartilhável; licença, quota e gate de leitura |
| GET | `/api/tools/magic-formula/stocks/{company_id}` | `magic_formula_stock_detail` — [dashboard.py:661](../src/income_analytics/api/routers/dashboard.py) | Referência compartilhável; licença, quota e gate de leitura |
| POST | `/api/trades` | `create_trade` — [dashboard.py:2323](../src/income_analytics/api/routers/dashboard.py) | Privado por padrão; autenticação e proprietário da carteira/recurso |
| GET | `/health` | `health` — [health.py:7](../src/income_analytics/api/routers/health.py) | Público mínimo (shell/health); sem dados financeiros |
| POST | `/imports/b3/preview` | `preview_b3_import` — [dashboard.py:2627](../src/income_analytics/api/routers/dashboard.py) | Privado; alias legado também deve exigir proprietário |
| POST | `/imports/b3/{batch_id}/apply` | `apply_b3_import` — [dashboard.py:2665](../src/income_analytics/api/routers/dashboard.py) | Privado; alias legado também deve exigir proprietário |

## Cobertura por experiência

| Experiência | Famílias auditadas |
|---|---|
| Minha Carteira | `/portfolio`, `/portfolio/dashboard*`, `/portfolio/holdings`, `/portfolio/history`, `/portfolio/class-allocation`, `/operations` para rendimentos |
| Entender | `/analytics/wealth-*`, `/analytics/performance-comparison`, `/portfolio/performance`, `/portfolio/benchmark-comparison`, risco/intelligence |
| Estratégia | `/allocation-policy`, `/asset-allocation-policy`, `/portfolio/allocation*`, rebalancing, reclassificação de ativo |
| Simular | `/portfolio/simulation/contribution`, `/portfolio/rebalancing/*`; POST analítico ainda lê patrimônio privado |
| Operações | `/trades`, `/external-flows`, `/dividends`, `/jcp`, `/fii-income`, `/fixed-income/sales`, `/operations*`, recorrências |
| Income Starter | catálogo, modelos e adoção; active-strategy e jornada de reserva são privados |
| Magic Formula | `/tools`, `/tools/magic-formula/*`; armazenamento público separado do ledger, curadoria/ingestão não é rota pública de usuário |
| Configurações | carteira/moeda, paid-income global, provider health, reset, refresh de referências |
| Importações | B3/IRPF preview/apply/history e aliases sem `/api`; nome, instituição e linhas são privados |
| Relatórios/exports | Sem rota de download dedicada; respostas JSON privadas, dados de auditoria e futuros exports devem exigir ownership |

A proteção futura precisa cobrir todos os métodos, aliases e acessos indiretos, não apenas o menu visual ou o prefixo `/api/portfolio`.
