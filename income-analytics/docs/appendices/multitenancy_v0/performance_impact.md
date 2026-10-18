# Performance impact

SQLite is viable for local V1/V2 if filters are applied in SQL before rows enter memory. New ownership columns widen rows/indexes and add write cost; likely composite indexes include `(portfolio_id, effective_date)`, `(portfolio_id, asset_id, effective_date)` and portfolio-scoped idempotency keys, finalized from measured query plans. Avoid current pattern of globally preloading all events and filtering in Python. Keep canonical assets/prices/FX/benchmarks shared and indexed by security/date. Analytics receive scoped inputs; formulas remain unchanged. Snapshot/cache keys include portfolio and revision.

SQLite remains suitable for local modest serialized writes. Reassess PostgreSQL for hosted concurrent writers, multi-process workers, HA/replication, operational backup requirements or measured lock/latency limits—not merely because portfolio_id is added. Retain existing performance baseline and measure query counts/latency after scoping.
