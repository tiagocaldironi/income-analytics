# Proposed release applicability policy

**State: proposed, not approved for production use.** The evaluator deliberately
returns `BLOCKED` for every proposed `NOT_APPLICABLE` result until a GitHub
approval is bound to the canonical digest of this policy. No financial or
historical evidence is changed by this proposal.

## Current blocker classification

The current financial report identifies three evidence blockers, not a newly
observed calculation regression:

| Control | Current finding | Evidence boundary |
|---|---|---|
| `CERT_48` | Frozen Formula engine bytes do not match their approved manifest. | `tests/application/test_historical_shares_units.py::test_shares_unit_020_frozen_engine` compares three pinned `magic_formula_*` modules. The manifest and hashes remain untouched. |
| `IDENTITY_PROVENANCE_UNAPPROVED` | Original identity authorization at the historical cutoff is unavailable. | The frozen `price_identity_v1` record is consumed by `historical_security_identity.recover_price`; source search finds its production caller in `magic_formula_price_blocker_batch.py`. The current fixture explicitly says `historical_mapping_approved: false`. |
| `22_HISTORICAL_REFERENCES_UNAPPROVED` | The original complete universe/ranking and CVM/B3 evidence chain is unavailable or unapproved. | The 22 failing/erroring node IDs are Formula API, ranking, historical price, methodology and preview tests. The provenance policy enumerates the corresponding 17 source/reference IDs. |

The 22 cases remain in full Python and financial diagnostic reports. Their
classification as historical evidence failures does not turn them into passes.

## Dependency findings from the current source tree

- The frozen `CERT_48` manifest names only `magic_formula_stocks.py`,
  `magic_formula_ranking_validation.py` and `magic_formula_contract.py`.
- The 22 historical tests exercise Formula API/ranking/snapshot behavior and
  their historical market/reference inputs.
- `historical_security_identity.recover_price` is called by
  `magic_formula_price_blocker_batch.py`; the identity fixture test exercises
  that same helper. No call from portfolio, Treasury or SQLite transaction
  modules was found in the source search.
- `historical_shares_units.py` is imported by its Formula-oriented test module;
  the CVM evidence reader has no other product-code caller in the current
  source tree. This is a static repository result, not a claim about unknown
  runtime plugins or future imports.
- Portfolio/Treasury release independence requires same-candidate scoped test
  execution, a transitive static import closure over every changed Python
  module, source digests for every traversed module, and the runtime dependency
  trace. Dynamic imports, parse failures, missing changed files or unresolved
  internal imports keep the analysis incomplete and block `NOT_APPLICABLE`.
  Static analysis alone is insufficient; runtime evidence remains required.

## Applicability matrix

| Candidate change scope | CERT_48 | Identity provenance | 22 historical references | Core financial tests | Required handling |
|---|---|---|---|---|---|
| CSS-only visual change | `NOT_APPLICABLE` only after policy approval and complete dependency proof | Same | Same | `NOT_APPLICABLE` after approval; frontend suites, security, build and staging still apply | Any HTML, JavaScript, API, auth, backend, test, workflow or unclassified file makes the scope unknown/shared and blocks this row. |
| Portfolio/Treasury calculation or persistence | `NOT_APPLICABLE` only after policy approval and no Formula dependency | Same, unless identity modules are touched/reached | Same | `PASS` required for all tests and controls mapped to the changed financial modules | A new regression is `FAIL`; missing tests/trace is `BLOCKED`. SQLite fixtures, migration and rollback checks remain required when applicable. |
| Formula Mágica or its historical source/ranking path | `PASS` required; current bytes keep this `BLOCKED` | `PASS`/approved provenance required; current state `BLOCKED` | `PASS`/approved references required; current state `BLOCKED` | Relevant core financial controls also run if shared paths are touched | No bypass or reinterpretation of the three Formula blockers. |
| API, authentication, authorization, database, shared code, CI/security policy, mixed or unknown scope | `BLOCKED` until full dependency impact is resolved | Same | Same | Applicable financial tests plus all security/build/staging controls | Fail closed; no assumed independence. |

## Decision and evidence rules

The candidate evaluator in `ci/release_applicability.py` emits per-control
`PASS`, `FAIL`, `BLOCKED` or `NOT_APPLICABLE`, reasons, changed scopes and the
observed dependency modules. `ci/release_dependency_analysis.py` resolves the
transitive static import closure from changed Python modules and records a
SHA-256 for each traversed source file. That result is combined with the
same-candidate runtime trace; dynamic imports, unresolved internal imports,
parse errors, or missing files keep dependency evidence incomplete. An
applicable control cannot be supplied as `NOT_APPLICABLE`. An unknown path,
missing result, incomplete static or runtime dependency evidence, or a
protected module in either graph blocks eligibility. `NOT_APPLICABLE` requires
an approval record and exact policy digest; synthetic test approvals are only
unit-test inputs and are not production approvals.

Security, reproducible build and staging remain mandatory for every scope.
`merge_authorized` and `deployment_authorized` remain false. The historical
financial evaluator, frozen manifests, SQLite data and backup/rollback
mechanisms are not modified.

Local synthetic tests exercise eligible CSS-only and core-financial scopes only
when supplied an approved-policy fixture, and verify transitive imports,
dynamic-import blocking, unknown paths, missing static/runtime traces, observed
Formula dependencies, unapproved policy, and financial failures remain
blocked. Those fixtures validate evaluator behavior; they are not evidence
that a real candidate has been approved or is eligible.
Focused local validation on Python 3.14 passed 73 scoped-promotion and scoped
financial tests; Ruff and bytecode compilation passed. The repository Treasury
import closure resolved 17 modules with no Formula dependency and complete
evidence. The current policy digest must be re-reviewed after these changes.

## Approval needed before activation

The policy is not yet approved. The required audit record must reference the
canonical SHA-256 of `ci/release-applicability-policy.json`, identify the
repository owner `tiagocaldironi` as approver, and bind an immutable GitHub comment containing
`RELEASE_POLICY_APPROVED <policy-sha256>`. Until that record is reviewed and
the hosted promotion job runs against the candidate on `develop`, the production
decision remains `BLOCKED`; this proposal cannot generate an eligible production
release by itself.

For the existing scoped promotion record, the approval comment must also contain
`OWNER_APPROVED <candidate-sha>`. The two JSON records will reference the same
GitHub comment ID, URL and body digest. Approval-record metadata is authenticated
against that external comment and is excluded from the protected code surface;
the evaluator, policy, tests and dependency map remain in the protected surface.

The existing PR-specific promotion path for PRs 69, 79 and 81 is preserved. New
candidate runs use the explicit `release-candidate` label: the core workflow
runs the full Python suite once, derives financial evidence from that JUnit,
then binds both reports to the same run identity. The diagnostics workflow
skips the duplicate full/financial execution while the label is present.

The `pull_request` workflow trigger targets `develop`. PR #86 is integrated,
and PR #87 now targets `develop`; its ordinary hosted CI has run. The candidate
promotion path remains blocked until the policy owner records the exact policy
approval and the candidate has an applicable changed-file scope. This report
does not claim that a hosted eligible release decision has occurred.
