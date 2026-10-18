# Income Analytics — Multitenancy Readiness Audit V0

**Status:** read-only architectural audit; no migration, schema/API/calculation/frontend edits, or database writes. **Date:** 2026-10-18.

## INCOME_ANALYTICS_MULTITENANCY_READINESS_AUDIT_V0 = FAIL

The current runtime is not safe for multiple portfolios/users. This is an architecture readiness failure, not an instruction to implement changes.

## CURRENT STATE

- `TABLES = 36` tables across primary database and three `data/magic_formula/*.db` files: 35 business tables plus `alembic_version`; `VIEWS = 0`. The primary DB has 28 business tables: 24 ORM models + 4 raw SQL Magic Formula tables. Separate MF DBs have 1 universe, 5 canonical ranking and 1 validation artifact table.
- `MIGRATION_HISTORY = 18 revisions; current = 0018_portfolio_price_refresh_runs`.
- Across all business tables: portfolio-owned 12, user-owned 1, derived portfolio 1, global reference 14, system 6, uncertain 1. Primary DB only: portfolio-owned 12, user-owned 1, derived portfolio 1, global reference 10, system 3, uncertain 1. Counts classify tables, not personal row counts.
- `PORTFOLIO_ENTITY_EXISTS = NO`; `USER_ENTITY_EXISTS = NO`; `MEMBERSHIP_EXISTS = NO`. `PortfolioSession` is an application object only, not persisted portfolio aggregate.
- `CURRENT_SINGLE_PORTFOLIO_ASSUMPTION = HIGH`; `SQLITE_MULTI_PORTFOLIO_FEASIBLE = CONDITIONAL` for local V1/V2 with SQL-first scoping and serialized writes.
- `API_DECLARATIONS = 81`; `DISTINCT_METHOD_PATHS = 79` (B3 preview/apply are mounted on two routers). `UNSCOPED_ENDPOINTS = 44` clearly portfolio-required declarations. No authentication/membership boundary found.
- `UNSCOPED_REPOSITORIES = 14` repository classes (35 methods) operate on portfolio-owned data without portfolio context; one more repository is uncertain. `PortfolioSession` loads all current assets/events and singleton policy/config. `financial_events.account_id` is indexed but has no FK and does not scope requests.
- High-risk cache/state: global B3 preview cache, performance comparison LRU without portfolio key, dashboard snapshot singleton id=1, module-global `PortfolioSession`.
- All portfolio analytics/read models (holdings, wealth, explanation, TWR, performance comparison, findings, operations/income) derive from that global session; only dashboard JSON is persisted among these outputs.

## DATABASE / MODEL FINDINGS

`allocation_targets` uses only asset-class key, `asset_targets` only asset ID, `portfolio_configuration` is key/value singleton, dashboard snapshot is id=1. Paid-income fingerprint and B3 import identity are globally unique today. These constraints need owner-semantic review before composite keys. Global `assets` is mixed: canonical ticker identity coexists with user-created assets, class changes and private instrument details.

Keep market prices, FX, benchmarks, CVM/B3 reference records and canonical Magic Formula universe/ranking shared. Keep `MF_BR_2027_V1` untouched. Separate future user screening preferences from canonical ranking. Keep TWR/wealth formulas unchanged by filtering inputs before engines.

## MIGRATION / TARGET

`CURRENT_DATA_CAN_BE_MIGRATED_TO_DEFAULT_PORTFOLIO = YES, CONDITIONAL`; `ZERO_LOSS_MIGRATION_PATH = YES, CONDITIONAL` via backup, stable row IDs, ownership reconciliation and golden pre/post hashes. Do not assume `account_id == portfolio_id`.

`USER_1_TO_N_PORTFOLIOS = SUPPORTED_BY_PLAN YES`; `PORTFOLIO_ISOLATION = SUPPORTED_BY_PLAN YES`; `SHARED_MARKET_DATA = SUPPORTED_BY_PLAN YES`; `FUTURE_SHARED_PORTFOLIO = SUPPORTED_BY_PLAN YES (membership deferred to V3)`.

Highest risks: ledger/session isolation, snapshot/cache leakage, import apply ownership, mixed asset model, token ownership, user authorization, scoped uniqueness and no-loss history migration.

## RECOMMENDED NEXT STEP

**V1 — Portfolio Domain Foundation:** define stable Portfolio and `MAIN_PORTFOLIO`; capture baseline hashes; reconcile legacy assets/events/imports; add scoped repository and service contracts with SQL-level filtering; backfill and verify before NOT NULL. Preserve shared reference data and formulas.

**DO NOT IMPLEMENT V1 AUTOMATICALLY. STOP AFTER AUDIT.**

Detailed inventories and diagrams: `docs/appendices/multitenancy_v0/` (CSV ownership, DB constraints, repositories, services, caches, read models, API routes, frontend, migration impact and risks; plus current/target architecture, migration/test/performance plans). API paths are router-local (dashboard router is mounted under `/api`); B3 preview/apply declarations are duplicated by mounts. Database inspection used read-only SQLite connections; no personal payloads or credentials were copied to these artifacts.
