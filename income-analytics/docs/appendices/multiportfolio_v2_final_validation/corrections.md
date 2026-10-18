# Corrections

`V2-01` corrected a portfolio-scoped dashboard read-model defect. Creating an empty portfolio now prepares its dashboard snapshot before returning. The dashboard and holdings read routes now choose the snapshot repository from the validated `X-Portfolio-Id` request header (MAIN is the legacy headerless fallback), rather than relying on worker context. The new regression checks HTTP 200, empty positions/classes, and equality between snapshot and direct portfolio projection while MAIN has independent data. Financial formulas and event semantics did not change.

`TEST-01` corrected test isolation only: the missing-read-model test now patches the repository factory method rather than retaining a bound method on a proxy instance. Assertions were not relaxed.

No migration was needed. No pre-existing product defects were changed.

`TEST-02` fixed stale test state: the pytest SQLite filename was based only on process ID, which Windows can recycle after process exit. The test database now uses a UUID per run, preventing a prior run's financial data from contaminating later tests. The focused persistence, multiportfolio, history-boundary, and operation-history group passed (27 tests).
