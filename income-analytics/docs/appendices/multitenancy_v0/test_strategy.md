# Required tests

Build two-user/two-portfolio fixtures with shared canonical assets and quotes but divergent quantities, events, policies, income, imports, snapshots and revisions. Assert: A data never appears in B; B writes leave A analytics unchanged; both portfolios can consume one shared quote; same asset has independent holdings/targets; import preview/history/apply is owner-bound; matching revisions cannot cross cache keys; forged IDs and missing membership are rejected; OWNER/EDITOR/VIEWER permissions work; archive/delete B does not change A; benchmark/FX/MF canonical data remain shared.

Migration checks compare IDs/counts and golden MAIN_PORTFOLIO payload hashes; detect dropped/duplicated/reassigned events; test repeatability, rollback/restore and import idempotency. Repository tests must prove SQL predicates apply before materialization, not just filter results in Python. Exercise SQLite concurrent reads/writes, locks, recurrence jobs and transactional imports.
