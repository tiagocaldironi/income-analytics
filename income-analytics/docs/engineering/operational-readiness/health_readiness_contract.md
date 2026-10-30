# Health and readiness

`GET /health` retains its original response. The outer ASGI operational middleware provides
`GET /health/live` (process can answer, no dependency I/O) and `GET /health/ready` (lifespan startup complete,
read-only SQLite connection, query and exact Alembic head). Failure returns 503 and only
`{"status":"unavailable"}`; success 200 and `{"status":"ok"}`. No paths, versions, users or exception messages.
SQLite probe timeout is 100ms; no writes, migration, checkpoint or external call. Compatibility is
head-based, not a full structural integrity scan. Offline DR exercises additionally run integrity_check
and exact synthetic semantic signatures. Health is not evidence of financial correctness.

`GET /health/status` requires a distinct `INCOME_OPERATIONAL_TOKEN` of at least 32 characters,
matched in constant time against the Authorization bearer header. Unset/short/incorrect credentials
return 401. No default credential, user cookie shortcut or cloud provisioning. The token is never logged.
Responses use no-store. Method mismatch returns 405. The middleware runs before portfolio middleware,
so probes do not load or recompute financial sessions. Operators must restrict network reachability
and provision a real secret later. This PR does not activate endpoints on a productive process.

Implementation: `src/income_analytics/infrastructure/operational.py`; tests:
`ci/test_operational.py`. Lifecycle, unavailable DB, incompatible schema, recovery and collector faults
are exercised with synthetic databases. A process killed before Python startup cannot emit an event;
external supervisor monitoring is a host prerequisite, not simulated by liveness.
