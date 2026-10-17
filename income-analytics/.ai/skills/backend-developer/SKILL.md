# Backend Developer Skill

## Process

Follow DISCOVER, UNDERSTAND, IMPACT ANALYSIS, PLAN, IMPLEMENT, TEST, SELF
REVIEW and READY_FOR_QA. Before changes, locate entities, use cases,
repositories, endpoints, DTOs, migrations, integrations and related tests.
Reuse existing patterns in the Python, FastAPI, SQLAlchemy, Alembic and pytest
codebase.

## Impact and financial integrity

Evaluate domain, data, API, integrations, security, performance and regression
impact. Persisted changes require attention to legacy data, nullable/defaults,
constraints, indexes, duplication, replay and idempotency.

Use existing representations for money, quantity, percentages, currencies and
dates. Do not use binary floating point for financial business rules. Do not
assume BRL, integer quantities, percentage scale or that acquisition,
transaction, settlement, record and payment dates are interchangeable. Record
DOMAIN_QUESTION when the task is insufficient.

## Integrations and tests

Treat providers as untrusted: timeout, rate limit, partial payload, changed
contract, duplicate records and reprocessing must be evaluated. Keep provider
formats out of the domain.

Test happy paths, optional and invalid input, boundaries, precision,
duplicates, idempotency, historical data, persistence and integration failure
when applicable. For bug fixes, reproduce before correcting whenever feasible.

## Report

Produce BACKEND_DEV_REPORT with understanding, impact analysis, contract/data
changes, files, decisions, tests actually executed, regression considerations,
risks, assumptions, domain questions, frontend impact, QA focus and status.
