# PR11 — Engineering debt closure

State: ENGINEERING_DEBT_PARTIALLY_CLOSED. Hosted validation and protected integration are pending in this documentation snapshot; hosted_validation.json and the final PR receipt distinguish their eventual results. ENGINEERING_DEBT_CLOSED is not claimed.

Reference: PR10 #55, develop `cfb96a2b405b2821d7b03a6a3546dd8c9241d8c0`, CI run 41051244098. Read-only preflight confirmed the effective ruleset 26078982 and mandatory CI / Engineering. Work is isolated on codex/pr11-engineering-debt; the original checkout and existing worktrees are preserved.

Baseline: 130 Ruff + 672 mypy = 802 occurrences. Candidate: 0 Ruff + 607 mypy = 607. 195 observed occurrences resolved, no invented independent-defect count, no lint/type suppressions. The original historical quality baseline has 803 entries; the one previously removed before PR10 remains separately accounted for in quality_ledger.json. The original file is unchanged. New debt or reintroduced resolved debt fails non-regression.

The Ruff promotion extends the existing Engineering check with fail-closed same-commit/source/policy/run/attempt evidence. mypy and Full Python remain diagnostics until legitimately clean; ruleset and financial gate are unchanged. Negative tests cover missing/failed/skipped/cancelled reports, inconsistent identity, duplicate debt, missing inventory, changed source review, and reintroduction of resolved occurrences.

Runtime changes are concrete types, middleware contracts and a transactional onboarding invariant. Executable AST comparisons establish equivalence for the edited production, migration and existing test files after explicitly accounting for annotations, added type declarations, the row assertion and a local variable rename. No arithmetic or financial predicate was changed. No existing test assertion or expected value was changed. See regression_comparison.json for limits and checks.

Financial certification remains FINANCIAL_CERTIFICATION_BLOCKED. Full Python retains all historical financial cases and external tests. No deploy, production migration, Firebase/Tailscale change or data reconciliation occurs. Build and disposable staging must still pass through the existing pipeline.

Commands (locked Python 3.14.7 environment): `python ci/governance.py ruff`, `mypy`, `quality`, `engineering`, `python`, `financial`, `operational`, `node`, `runtime`; `python ci/build_pipeline.py` in a clean committed checkout. Each governance command writes sanitized result/JUnit/inventory reports. Refer to the root .github/workflows/ci-offline.yml for exact locked installations and hosted jobs. Reports and immutable artifact digests are bound to the tested SHA; local evidence alone is insufficient for closure.

Required evidence: diagnostics_baseline.json; diagnostics_inventory.csv; root_cause_analysis.md; corrections_matrix.csv; ruff_validation.json; mypy_validation.json; full_python_validation.json; regression_comparison.json; ci_gate_hardening.json; hosted_validation.json; remaining_debt.md. quality_ledger.json is the additional audited occurrence/location policy.

Local candidate regression: Python engineering 1365 passed, operational 64 passed, frontend PASS, quality non-regression PASS, financial 104 passed / 15 failed / 9 errors. Full Python repeat is pending. These preliminary local runs are not represented as final same-SHA hosted approval.
