# Remaining engineering debt

Status: ENGINEERING_DEBT_PARTIALLY_CLOSED (candidate; hosted integration not yet verified).

Ruff is locally clean. mypy remains failed with 607 occurrences; Full Python remains failed on its existing financial/historical contract. Neither is promoted. No exception, skip, xfail, exclusion, financial expected value, frozen file or lint/type rule was added to conceal these results.

Remaining mypy diagnostics by rule:

- `no-untyped-call`: 206
- `no-untyped-def`: 134
- `type-arg`: 65
- `attr-defined`: 51
- `arg-type`: 34
- `operator`: 28
- `union-attr`: 28
- `no-any-return`: 18
- `assignment`: 14
- `var-annotated`: 12
- `return-value`: 5
- `index`: 4
- `type-var`: 3
- `misc`: 2
- `no-redef`: 1
- `import-untyped`: 1
- `dict-item`: 1

Every file/line and remediation is in diagnostics_inventory.csv. Untyped callees must be addressed before propagated call-site diagnostics; nested financial JSON/evidence models need explicit shapes and before/after replay, not blanket Any. SDK typing must track the installed Firebase version rather than weakening strict mode. Nullable contracts must distinguish impossible state from genuinely absent financial data.

Release blocker: FINANCIAL_CERTIFICATION_BLOCKED, including CERT_48 and missing independently approved historical provenance. This PR cannot lawfully synthesize that evidence or alter frozen hashes. The Full Python contract cannot become a passing mandatory gate while it retains these legitimate failures. Its execution is preserved.

Merge eligibility is separate from debt closure: all existing mandatory checks plus the clean Ruff promotion must pass; mypy/full/financial failures remain visible. A partial merge never authorizes beta or production and cannot be reported as ENGINEERING_DEBT_CLOSED.
