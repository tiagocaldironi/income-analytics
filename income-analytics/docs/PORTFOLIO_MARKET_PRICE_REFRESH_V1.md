# Portfolio market price refresh V1

## Discovery

```text
BRAZIL_REFRESH_CURRENT_FLOW = POST /api/market-prices/refresh -> PortfolioSession -> BRAPI/B3 fallback -> market_prices -> dashboard snapshot
CRYPTO_PROVIDER_FOUND = CoinGeckoCryptoProvider
CRYPTO_PROVIDER_STATUS = OPERATIONAL (BTC real quote returned in USD on 2026-09-23)
US_PROVIDER_FOUND = TwelveDataUSMarketProvider
US_PROVIDER_STATUS = CONFIGURED_AND_OPERATIONAL (MCD real quote returned in USD on 2026-09-22)
FX_CURRENT_FLOW = BcbFxRateProvider USD/BRL -> fx_rates -> BaseCurrencyValuationProjector
CACHE_CURRENT_FLOW = persisted market_prices plus persisted dashboard snapshot; reads do not call providers
PERSISTENCE_CURRENT_FLOW = market_prices, now with provider and price_timestamp; market_price_refresh_runs
```

The existing Brazilian refresh was generalized. It routes `CRYPTO` to CoinGecko;
`INTERNATIONAL` (the project's canonical US-stock class), `INTERNATIONAL_ETF`, and
`US_REIT` to Twelve Data. Brazil equities and FIIs retain the BRAPI-first/B3 fallback.
No Magic Formula source, table, date policy, or ranking input is used.

Native prices remain native: USD quotes are never written as BRL. The asset master
provides the native currency, and a quote with a conflicting provider currency is
rejected. Consolidation uses the already existing USD/BRL PTAX record, including its
source and effective date; price and FX are not multiplied into a stored quote.
Crypto keeps the pre-existing USD policy. CoinGecko now batches its simple-price call
after resolving/caching canonical coin IDs. Twelve Data attempts bounded batches of
eight symbols, then falls back only for symbols omitted or rejected by the plan.

## Result

```text
PORTFOLIO_MARKET_PRICE_REFRESH_PHASE = PARTIAL
BRAZIL_PRICE_REFRESH = ACTIVE
CRYPTO_PRICE_REFRESH = ACTIVE
US_STOCK_PRICE_REFRESH = ACTIVE_WITH_PROVIDER_LIMIT
INTERNATIONAL_ETF_PRICE_REFRESH = ACTIVE_WITH_PROVIDER_LIMIT
REIT_PRICE_REFRESH = ACTIVE_WITH_PROVIDER_LIMIT
CRYPTO_PROVIDER = COINGECKO
US_PROVIDER = TWELVE_DATA
FX_PROVIDER = BCB_PTAX
BATCH_REFRESH = ACTIVE
CACHE_STATUS = PERSISTED_BACKEND_READ_MODEL
PERSISTENCE_STATUS = PASS
PARTIAL_FAILURE_HANDLING = PASS
CURRENT_PRICE_UPDATED_AS_OF = provider effective date, never fabricated intraday
PORTFOLIO_RECALCULATION = PASS
MAGIC_FORMULA_REGRESSION = PASS
TESTS_PASSED = 25 (targeted regression after this change)
TESTS_FAILED = 0 (targeted regression)
LINT_STATUS = PASS (changed price-refresh files)
```

The real provider checks returned a positive MCD/USD close for 2026-09-22 and a
positive BTC/USD quote for 2026-09-23. The production-like local refresh then
encountered the Twelve Data plan/rate limit after diagnostics. Its persisted run
`1f82b474-d348-4b2d-bcda-b55d7210b1e9` is `PARTIAL`: it records the 12 requested US
symbols, the provider failure, and the stale USD/BRL FX already available. No price
was zeroed or replaced with null. This is a live validation of partial-failure behavior,
not proof that the Twelve Data allowance supports the full local portfolio indefinitely.

The project must retain a valid Twelve Data allowance or choose another approved US
provider before the result can be called fully operational for all 12 US holdings.
No provider was purchased, substituted, or assumed automatically.

## Persistence, API, and UI

Migrations `0017_portfolio_market_price_lineage` and
`0018_portfolio_price_refresh_runs` were applied to the local database. The migration
read-back in a fresh connection confirmed `provider` and `price_timestamp` on
`market_prices`, plus the append-only refresh-run table. Automatic backups were created
at `backups/income_analytics-20260923T104921Z.db` and
`backups/income_analytics-20260923T105409Z.db` before the respective migrations.

`POST /api/market-prices/refresh` returns a run ID and each provider's requested,
resolved, failed, status, and duration fields. It updates the persisted dashboard only
after a quote or FX update. `GET /api/portfolio/holdings` exposes `price_as_of`,
`price_provider`, `price_retrieved_at`, and `price_timestamp`; Minha Carteira displays
the quote date beside the asset. Opening the screen remains a read-model request.

## Validation

New tests cover BTC/ETH, US stock, ETF, REIT, Brazil equity/FII, provider grouping,
deduplication, native currency rejection, batch fallback, CoinGecko batch normalization,
partial provider failure, FX valuation, and the mixed-portfolio calculation.

The mixed fixture has Brazil stock, FII, BTC, ETH, MCD, IVV and O. Its provider groups
are called once each; a USD/BRL rate of 5 yields a BRL market value of 71,170. The four
negative cases verify missing quote, invalid currency, unavailable provider, and stale
existing value behavior. The Magic Formula preview and price-identity fixture regressions
also pass: preview remains active, ranking gate remains blocked, ranking remains inactive,
and the Golden Five remains unchanged.

An unrelated pre-existing acceptance test still expects `REVIEW_REQUIRED` in
`operations.js`; that string is absent before and after this work and was not changed.

## Files

- `src/income_analytics/application/market_data.py`
- `src/income_analytics/application/portfolio_session.py`
- `src/income_analytics/domain/market_price.py`
- `src/income_analytics/infrastructure/coingecko_crypto_data.py`
- `src/income_analytics/infrastructure/twelve_data_us_market_data.py`
- `src/income_analytics/infrastructure/models.py`
- `src/income_analytics/infrastructure/sqlite_repositories.py`
- `src/income_analytics/api/routers/dashboard.py`
- `src/income_analytics/api/static/js/features/portfolio.js`
- `src/income_analytics/api/static/js/features/operations.js`
- `alembic/versions/0017_portfolio_market_price_lineage.py`
- `alembic/versions/0018_portfolio_price_refresh_runs.py`
- `tests/application/test_portfolio_market_price_refresh.py`
- `tests/infrastructure/test_coingecko_crypto_data.py`
- `tests/infrastructure/test_twelve_data_us_market_data.py`
