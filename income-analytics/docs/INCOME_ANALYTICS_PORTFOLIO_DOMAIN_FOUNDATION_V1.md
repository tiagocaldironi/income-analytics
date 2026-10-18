# Portfolio Domain Foundation V1

This migration gives the existing local portfolio an explicit, stable ownership boundary while keeping the current single-portfolio interface and API URLs.

## Architecture

`Portfolio` is persisted with deterministic `MAIN_PORTFOLIO` ID `7a54eeb7-542a-5832-8544-8be7dcb0237e`. The application composition boundary resolves the legacy single-portfolio request to that ID; repositories and `PortfolioSession` receive an explicit portfolio ID. HTTP requests receive a portfolio-scoped session through request context, so portfolio-derived state is not held in a module-global session.

Portfolio-owned rows carry a required foreign key to `portfolios`. Asset membership is represented by `portfolio_assets`; canonical asset identity and market prices remain shared. The exact pre-migration snapshot contained 86 assets; all were linked to MAIN without copying global asset or price rows. Financial events and asset-specific records validate that referenced assets belong to the same portfolio.

Configuration, class targets, asset targets, B3 imports, paid-income imports, quote-refresh runs, and dashboard snapshots are portfolio-scoped. The performance-comparison cache and B3 preview cache include the portfolio ID. Shared quote/index and benchmark caches are keyed by database identity; financial-event snapshots are additionally keyed by portfolio ID and invalidated on event writes and B3 transaction commits. FX, benchmark observations, provider health, and Magic Formula canonical ranking remain global.

## Migration and reconciliation

Alembic revision `0019_portfolio_domain_foundation` follows `0018_portfolio_price_refresh_runs`. It creates MAIN, links existing assets, adds nullable ownership columns, backfills legacy rows, validates relationships, then enforces ownership and scoped constraints. A repeated upgrade is a no-op and does not create another main portfolio.

A verified backup was made before the production migration. Both the exact current 0018 snapshot and a fresh empty database were migrated on isolated copies; each passed integrity and foreign-key checks, and repeated upgrades were idempotent. The production database is now at 0019. The legacy B3 import table contained 44 optional event links to already-deleted financial events. The migration cleared only those stale `financial_event_id` pointers; imported source rows and financial events were preserved.

The full baseline, backup manifest, reconciliation, migration evidence, API hashes, and performance timings are in the local-only appendix `docs/appendices/portfolio_foundation_v1/`; these contain private portfolio data and are not committed. The API response hashes from old and new code match on the exact snapshot for portfolio, holdings, wealth evolution, performance, comparison, findings, allocation, and operations. The pre-existing wealth-explanation response remains HTTP 422 in both. Only the generated dashboard `calculated_at` timestamp was normalized.

## Validation and limits

The full suite passes 872 tests; Ruff passes. Portfolio isolation tests cover A-B-A/B-A-B session read models for holdings, wealth projections, performance, findings, independent targets, same global asset and quote, income fingerprints, dashboard snapshots, and B3 batch visibility. The migrated local runtime was restarted and health/portfolio HTTP endpoints were checked. Benchmark caches reduced request setup cost while preserving calculation outputs; measured warmed TWR latency is 1.31 s versus 1.17 s before, while findings improved from 222 ms to 207 ms.

This phase adds no users, authorization, portfolio selector, sharing, or deletion. V1 exposes only MAIN at the HTTP boundary, so arbitrary-portfolio API routing is not yet available. Pension investment vehicles are portfolio-owned while their quota observations stay global; review a shared vehicle/quota identity model before exposing multiple portfolios with pension products. SQLite continues to serialize writes. These are follow-on design items, not changes to the current single-portfolio behavior.
