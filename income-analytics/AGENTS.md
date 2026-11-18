# AGENTS.md — Income Analytics application

This file supplements the repository-root AGENTS.md and applies to the application under `income-analytics/`. Keep existing `.ai/agents`, `.ai/skills` and `.ai/workflows` instructions intact.

## Financial and operational safeguards
- Preserve financial calculations, historical records, SQLite data, migrations, idempotency and canonical transaction handling.
- Do not alter valuation, balances, import deduplication, authentication/authorization or persistence contracts without targeted regression tests.
- Never modify production data, deploy or change secrets as a side effect of a feature task.
- Distinguish engineering CI success from financial certification or release approval; one does not imply the other.

## Delivery sequence
1. Define functional acceptance criteria and affected modules.
2. Implement the smallest scoped change.
3. Run relevant unit/integration tests and financial invariants for affected code.
4. Record command outcomes, including any pre-existing failures.
5. Open a PR to `develop`; do not wait in a polling loop for GitHub Actions.
6. Summarize the PR, targeted test results and CI state, then end the session.

## CI failure policy
- **New regression:** fix before calling the change ready.
- **Existing unrelated failure:** document separately, without broadening the feature scope.
- **Required gate failure:** leave integration blocked; never disable the gate to obtain a green result.
- **Unresolved after two substantive attempts:** stop, capture concise evidence and recommend a dedicated follow-up.
- Read only failed step summaries and bounded excerpts, not full logs unless essential.

## Reporting
Use: scope delivered; changed files; targeted checks; financial/data integrity considerations; CI status (pending/passed/failed/unknown); blockers; next action.
