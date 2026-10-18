# Target architecture (concept only)

```mermaid
flowchart TB
 U[Authenticated User] --> M[PortfolioMembership: OWNER / EDITOR / VIEWER]
 M --> P[Portfolio]
 Q[Request principal + requested portfolio] --> G[Resolve identity; verify membership]
 G --> X[Authorized PortfolioContext]
 X --> APP[Application services / scoped repositories]
 APP --> OWN[(Portfolio ledger / imports / policies / details)]
 APP --> DER[(Per-portfolio read models / snapshots / caches)]
 APP --> ENG[Financial engines: same formulas, scoped inputs]
 APP --> REF[Shared reference repositories]
 REF --> MD[(Assets / prices / FX / benchmarks / CVM / B3)]
 REF --> MF[(Canonical Magic Formula universe / ranking)]
```

Required boundary: authenticated principal → requested portfolio → membership validation → scoped service/repository. Never authorize using a client-supplied portfolio ID alone. Identity is separate from finance domain. Keep global market and canonical Magic Formula data shared. A future consolidated `ALL_PORTFOLIOS` view is an aggregate projection, not another portfolio; transfer elimination and consolidated performance are out of scope here.
