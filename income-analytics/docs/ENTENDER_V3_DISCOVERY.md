# Entender V3 Discovery

## Current page structure

The Entender page currently contains period selection, Wealth Explanation, a derived-history table, Performance, and a Risk-in-period card. Wealth Explanation also renders standalone contribution-by-class and positive/negative-contributor cards.

## Existing working components

`WealthExplanationService` provides opening and closing wealth, reconciled signed components, unexplained change, data-quality coverage, and performance output. The V2.2 Contribution Explorer already applies progressive disclosure from component to largest impacts, class, and asset; zero-value children are hidden.

`PortfolioProjector` and `PortfolioHistory` reconstruct economic state from `effective_date`; `PerformanceProjector` uses external deposits and withdrawals as TWR boundaries. The completed [Temporal Semantics Audit V1](TEMPORAL_SEMANTICS_AUDIT_V1.md) confirms that creation and update timestamps are not used as economic dates.

## Evolution and endpoints

`GET /portfolio/history` returns derived snapshots grouped by period and is currently used by the dashboard and Entender. Before V3, Entender requested the global history (`period_months=0`) instead of the selected interval. It will be extended with optional economic start/end bounds and used by Entender only.

`GET /analytics/wealth-explanation`, `GET /portfolio/performance`, and `GET /portfolio/benchmark-comparison` currently accept explicit dates. V3 must cap end dates at today so no realised analysis includes a future date.

## Performance discovery

The TWR engine is shared and correct: it requires complete opening and closing valuations and dated values around external cash-flow boundaries. BUY, SELL, and paid income are not external flows. In the current local data, historical prices begin on 2026-09-07 and historical FX is incomplete; consequently a 2026-01-01 opening valuation cannot be complete and the insufficient-performance state is correct. This is source-coverage insufficiency, not a frontend or TWR-engine defect.

The benchmark engine compounds configured dated benchmark observations. It can return a portfolio TWR without a benchmark when no benchmark observations are configured; that must not suppress the portfolio performance result.

## Snapshot and cache

Portfolio history is reconstructed from source streams on demand. The dashboard snapshot is only a current-state read model and is rebuilt after portfolio writes. It is not used as a historical as-known-at source for Entender.

## V3 dependencies

1. Keep Wealth Explanation and Contribution Explorer unchanged as the source of explanation detail.
2. Bound every Entender endpoint by the selected effective period.
3. Remove independent contributor, class-contribution, and risk cards from Entender only.
4. Keep risk in Risco & Exposição and preserve shared backend endpoints.
