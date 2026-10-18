# Incremental plan (no V0 implementation)

**Before any migration:** backup every runtime SQLite file; capture source counts/IDs and golden hashes for operations/income, holdings/positions, dashboard, wealth history, performance payload, policies, import history and Magic Formula. Do not include secrets in artifacts. Reconcile custom assets, legacy account IDs and import ownership.

**V1 — Portfolio Domain Foundation:** add stable `Portfolio` and `MAIN_PORTFOLIO`; expand schema with nullable owner keys; backfill verified current portfolio rows; preserve IDs and `account_id`; add FK/index/composite constraints after reconciliation; replace global repository signatures with required portfolio context and filter in SQL. Key snapshots by portfolio. Compare baseline before enforcing NOT NULL. No login.

**V2 — Multiportfolio Local:** create/rename/archive and portfolio selector; scope ledger, recurring execution, policies, imports, read models and invalidation. Keep local single-user assumption explicit.

**V3 — Ownership Foundation:** add `User` and `PortfolioMembership`; enforce OWNER/EDITOR/VIEWER authorization at API/application boundary; isolate IDs, imports, caches and snapshots.

**V4 — Authentication:** login/session/logout and account lifecycle behind identity adapter; protect tokens/secrets.

**V5 — Multiuser Release:** HTTPS, secret storage, audit logs, backup/restore, concurrency, rate limits, incident and recovery processes. Never expose current unauthenticated local server as hosted multiuser.

Zero-loss path is **feasible conditionally**: preserve stable IDs and verify baseline; never assume `account_id == portfolio_id`. No database was modified by this audit.
