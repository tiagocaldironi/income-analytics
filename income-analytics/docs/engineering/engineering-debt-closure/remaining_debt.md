# Remaining engineering debt

Status: ENGINEERING_DEBT_PARTIALLY_CLOSED (candidate; hosted integration not yet verified).

Ruff has zero unjustified occurrences, with 23 visible and narrowly justified historical migration-style observations. The raw tool exits 1; the hash-pinned exception policy exits 0. mypy remains failed with 499 occurrences; Full Python remains failed on its existing financial/historical contract. Neither is promoted. No skip, xfail, exclusion, financial expected value, frozen file or lint/type rule was changed. Exactly 23 legacy style observations are justified under the specification exception clause, remain visible and have mutation tests.

Remaining mypy diagnostics by rule:

- `no-untyped-call`: 149
- `no-untyped-def`: 104
- `type-arg`: 62
- `attr-defined`: 46
- `arg-type`: 32
- `union-attr`: 28
- `operator`: 21
- `no-any-return`: 18
- `assignment`: 14
- `var-annotated`: 11
- `index`: 4
- `return-value`: 3
- `type-var`: 2
- `misc`: 2
- `no-redef`: 1
- `import-untyped`: 1
- `dict-item`: 1

Every file/line and remediation is in diagnostics_inventory.csv. Untyped callees must be addressed before propagated call-site diagnostics; nested financial JSON/evidence models need explicit shapes and before/after replay, not blanket Any. SDK typing must track the installed Firebase version rather than weakening strict mode. Nullable contracts must distinguish impossible state from genuinely absent financial data.

Release blocker: FINANCIAL_CERTIFICATION_BLOCKED, including CERT_48 and missing independently approved historical provenance. This PR cannot lawfully synthesize that evidence or alter frozen hashes. The Full Python contract cannot become a passing mandatory gate while it retains these legitimate failures. Its execution is preserved.

Merge eligibility is separate from debt closure: all existing mandatory checks plus the clean Ruff promotion must pass; mypy/full/financial failures remain visible. A partial merge never authorizes beta or production and cannot be reported as ENGINEERING_DEBT_CLOSED.

Concrete frozen-source constraint: 39 remaining mypy occurrences belong to magic_formula_stocks.py, magic_formula_ranking_validation.py and magic_formula_contract.py. All three are bound by frozen identity observations. Their existing bytes and five already-known mismatches are preserved. These 39 cannot be fixed by editing the source while also claiming unchanged frozen bytes. The other 460 occurrences remain explicit engineering debt; they are not reclassified as financial certification failures.
