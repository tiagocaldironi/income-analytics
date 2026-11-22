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
- Portfolio/Treasury release independence still requires same-candidate test
  execution evidence and a complete dependency trace. A source search alone is
  insufficient to approve a candidate.

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
observed dependency modules. An applicable control cannot be supplied as
`NOT_APPLICABLE`. An unknown path, missing result, incomplete dependency trace,
or call into a protected module blocks eligibility. `NOT_APPLICABLE` requires
an approval record and exact policy digest; synthetic test approvals are only
unit-test inputs and are not production approvals.

Security, reproducible build and staging remain mandatory for every scope.
`merge_authorized` and `deployment_authorized` remain false. The historical
financial evaluator, frozen manifests, SQLite data and backup/rollback
mechanisms are not modified.

Local synthetic tests exercise eligible CSS-only and core-financial scopes only
when supplied an approved-policy fixture, and verify Formula changes, unknown
paths, missing traces, observed Formula dependencies, unapproved policy, and
financial failures remain blocked. Those fixtures validate evaluator behavior;
they are not evidence that a real candidate has been approved or is eligible.
Focused local validation on Python 3.14 passed 65 tests across the applicability
evaluator, scoped-promotion controls and existing scoped financial controls;
Ruff, JSON parsing, bytecode compilation and `git diff --check` passed.

## Approval needed before activation

The policy is not yet approved. The required audit record must reference the
canonical SHA-256 of `ci/release-applicability-policy.json`, identify the
repository owner `tiagocaldironi` as approver, and bind an immutable GitHub comment containing
`RELEASE_POLICY_APPROVED <policy-sha256>`. Until that record is reviewed and
the implementation is integrated into the hosted promotion evaluator, the
production decision remains `BLOCKED`; this proposal cannot generate an
eligible production release by itself.
