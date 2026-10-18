# Current architecture (2026-10-18)

```mermaid
flowchart TB
 B[Browser: singleton API client] --> A[FastAPI; no auth boundary]
 A --> S[Module-global PortfolioSession persistent=True]
 S --> R[SQLite repos with unscoped list/get/save]
 R --> DB[(income_analytics.db)]
 S --> E[Portfolio / TWR / wealth engines]
 A --> SNAP[dashboard snapshot id=1]
 A --> C[global B3 preview + comparison cache]
 A --> REF[shared prices / FX / benchmarks]
 A --> MF[canonical Magic Formula DBs]
```

The browser calls `/api/...` with no portfolio context. Router handlers directly reuse one process-global persistent session that preloads the current dataset. `financial_events.account_id` is indexed legacy metadata, not a tenant boundary (no FK or authorization use). A dashboard JSON snapshot is a singleton. Shared market/reference data and user portfolio data coexist in one primary SQLite database; Magic Formula has separate SQLite files.
