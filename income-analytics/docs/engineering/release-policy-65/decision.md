# Issue 65 — controlled release proposal

Status: **NO-GO pending risk acceptance and financial evidence**, 2026-11-03.
Policy v1 principles explicitly approved by the user in this conversation;
see `policy_approval.json`. Exact baseline acceptance and activation are NOT approved.
This is not a requirement to eliminate all historical debt. No merge, production
deployment, baseline acceptance or financial exemption is authorized by this report.

## Exact candidate and evidence

- PR [62](https://github.com/tiagocaldironi/income-analytics/pull/62), head
  `eaae4df0f1f370bebd20d4299fd5e536de90d6f2`.
- Hosted CI [41612817516, attempt 1](https://github.com/tiagocaldironi/income-analytics/actions/runs/41612817516)
  tested merge `bb2db51085ee3ca6c5d9eadbbd439dab0b31cf96`, against develop
  `b642709a8ea3e89ebc27e2ae3c9ccbf7d4bccde4`.
- `baseline_*.json` and `candidate_*.json`: payload-free governance reports.
  The local Python baseline ran with preimplementation documentation present
  (`worktree_dirty=true`); production source was still the baseline. This limitation
  remains explicit; the clean hosted candidate is not substituted for the baseline.
- `comparison.json`: all preexisting test identities retain their statuses;
  31 new tests pass. Python: 1388→1419 passes, unchanged 15 failures, 9 errors,
  5 external skips. No skips or assertions were changed for this proposal.
- mypy: 499→486. Exact location comparison yields 87 apparent additions because
  lines moved. `mypy_inventory.json` records the original occurrence for every
  candidate occurrence using unchanged Git lines and exact code/message/multiplicity.
  All 486 map to prior occurrences; 39 are in frozen modules. This does **not**
  prove their runtime safety or that the enclosing functions are unchanged.
- The 137-diagnostic checkpoint mentioned in #64 was uncommitted P0 work, not
  a reproducible published baseline. It is not used here. Existing P0, PR12,
  original checkout and PR62 work are preserved in their original worktrees.

## Job matrix for PR62 attempt 1

| Job | Observed result | Release interpretation |
|---|---|---|
| Runtime, Python engineering, frontend | PASS | Supporting evidence |
| Build and installation | PASS | Reproducible package, not release approval |
| Ruff, quality non-regression | PASS | Existing exact policy, no scope reduction |
| Security baseline, operational readiness | PASS | Exact hosted candidate only |
| mypy | FAIL, 486 findings | Preexisting; individual risk acceptance pending |
| Full Python | FAIL, 15 failures / 9 errors | Preexisting, not silently accepted |
| Financial certification | BLOCKED, 104 passes / 15 failures / 9 errors | Separate scope/certification decision required |
| Staging rollback | FAIL, RESTORE_STATE_MISMATCH | New operational incompatibility exposed by cache v5 |

## Actual correction, rather than waiver

Candidate startup replaces the derived `portfolio_dashboard_snapshot` cache
(read-model version 4→5). Returning only the application to A leaves different
database contents, so the existing complete signature check correctly rejected
rollback. This is **not waived as historical debt**.

`restore_staging_checkpoint` now restores the verified checkpoint in the fresh,
owned disposable staging workspace, after stopping its processes. It compares
schema and rows in every persistent application table. Only cache contents may
differ. Insert/update/delete/schema changes elsewhere block recovery without
discarding facts. Cache schema changes also block. Final verification still uses
the complete original state signature; no table is excluded from that check.

`local_recovery.json` records the real published A/B artifact exercise passing
locally, including startup, backup, restore, rollback, negative controls and
cleanup. This is not evidence of hosted approval of the new correction. The
production rollback procedure is not implemented or certified by this change.

The report aggregator also now rejects Boolean/float exit codes that Python would
otherwise equate to integer zero. Negative controls reproduce the defect before
the fix. This strengthens existing gates.

## Scope and dependencies

| Scope in PR62 | Dependency / pertinent proof | Gate / unresolved decision |
|---|---|---|
| Treasury display groups, names, descending balances | dashboard projection and frontend; existing financial class retained | Engineering + UI regressions |
| Fractional Treasury purchases, sales, amendments | Decimal quantities, historical position coverage, persistence and owner isolation | Financial + Security; not merely cosmetic |
| B3 import and executable contribution plans | parser, pricing, rounding, budget/lot constraints | Integration + Financial; existing pass cases retained |
| Portfolio performance and totals | existing certified projectors, no frozen-code edit | Financial reconciliation, independently review CERT applicability |
| Startup cache v5 | snapshot persistence and old-version rollback | New rollback correction must pass hosted exercise |
| RendA+/Educa+ | #63 | Explicitly outside this work |

Frozen Magic Formula stock/ranking/contract modules do not directly implement
Treasury lot rules. However, the current financial gate certifies the broader
application and PR62 affects real financial transactions. Unchanged frozen
files alone cannot establish CERT_48 as NOT_APPLICABLE. #57 remains open:
canonical approval was not recovered, and LF/CRLF reconstruction is not approval.
An independent authority must approve either (a) the recovered/recertified
financial evidence, or (b) a narrowly documented release scope and alternative
pertinent certification. No financial policy is changed here.

## Backlog and remaining decisions

- #57: canonical CERT_48 / independent recertification or formal scope review.
- #58: 22 absent historical reference cases plus two frozen integrity failures;
  `test_inventory.json` retains all failures/errors and external skips. Missing
  reference data is distinct from an unproven B3 permission failure.
- #59 / #64: all 486 occurrence records, including each frozen occurrence's
  file, line, symbol, source text/hash, exact historical counterpart and issue.
  UNKNOWN risks require individual review. The 39 frozen occurrences have a separate
  per-ID technical review in `frozen_occurrence_reviews.json`, linked to #66 (10),
  #67 (28), #68 (1); low risk is proposed, not accepted. Proposed owner/deadline are not
  assignments or approvals. No generic allowance for the 39 frozen findings.
- #60: ruleset 26078982 currently requires CI / Engineering, up-to-date PRs,
  resolved discussions and no force push/deletion. The classic branch-protection
  endpoint returning 404 does not mean the ruleset is absent. No rules changed.
- #65: approve an exact reviewed low/medium-risk baseline, with per-occurrence
  evidence, owner and expiry. First complete the unknown-risk reviews; do not
  ask for blanket acceptance of this initial inventory.

## Decision sequence

1. Review this isolated PR and hosted results; fix any new failures.
2. Finish risk classification of occurrences relevant to the candidate and build
   narrowly scoped accepted-debt records for the rest. Split genuinely distinct
   causes into child issues after technical review, without duplicating #57–#64.
3. Obtain explicit approval of the policy version and exact accepted baseline
   digest. Approval of an idea is not acceptance of unknown financial/security risk.
4. Obtain independent financial certification/scope decision. Keep the failing
   CERT_48 result visible even if an approved scoped release is later possible.
5. Activate a reviewed regression gate in a subsequent authorized change, retaining
   all raw suites, full mypy scope and separate Financial/Security/Release results.
6. Validate the final combined commit in hosted CI, smoke/health and rollback.
   Only then issue a new GO/NO-GO. No automatic merge/deploy.
