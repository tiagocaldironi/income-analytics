# Zero-new-regressions policy — proposed v1, NOT APPROVED

This proposal implements the product decision in #65 without activating a new
promotion policy. Existing required checks, suites and financial gates are intact.
`ci/release_regressions.py` is a tested evaluator in **PROPOSAL_ONLY** mode; no
workflow or deployment controller calls it. It always reports
`deployment_authorized=false`, including when every proposed gate passes.

## Acceptance contract

The reviewed baseline must identify commit, full source/configuration, tool
versions, complete diagnostic occurrences and complete test identities/statuses.
Approval must reference the exact canonical JSON digest and a human review URL.
The designated approver and review deadline must be recorded. Updating a baseline
requires a new approval, not an automatic refresh from a failing candidate.

Each accepted diagnostic or nonpassing test needs a linked specific issue, owner,
review evidence, expiry, low/medium risk and individually reviewed noncritical
financial/security impact. Critical, high or UNKNOWN risk cannot be accepted by
this mechanism. The inventory's initial risk suggestions are not these decisions.

Exact fingerprints include tool, file, line, column, rule and message, preserving
multiplicity. A moved occurrence is initially new: a separate reviewed mapping can
justify a versioned baseline relocation, without silently normalizing line numbers.
New diagnostics, changed configuration/tool/scope, missing tests, new failing or
skipped tests, and pass→failure/error/skip transitions block. Existing failures and
external skips also require individual acceptance; their raw result remains visible.
Resolved debt may disappear; it is never offset against new debt by net counts.

Financial, Security and Release are independent blocking gates. An Engineering
baseline acceptance cannot change them. NOT_APPLICABLE is not implemented as a
Boolean flag; it requires an approved independent scope process. No negative
CERT_48 result can be renamed PASS, and no manifest/hash can be changed here.

The evaluator accepts prevalidated authenticated report objects. Authentication,
artifact provenance, approval authorization, source/commit binding and signature
verification must be supplied by the existing trusted CI orchestration before
activation. A string containing an approval URL is not itself proof of approval.
This module alone is not an enforceable production release authority.

## Reviewable implementation and reproduction

- Existing `ci/test_engineering_debt.py` is already collected by all existing CI
  scopes. It now exercises the proposed evaluator, including negative mutations,
  critical-gate independence and unchanged-line provenance controls.
- `ci/release_inventory.py` regenerates the inventory using four payload-free
  reports and Git blobs. Example from the application root:

```powershell
python ci/release_inventory.py `
  --baseline-mypy docs/engineering/release-policy-65/baseline_mypy.json `
  --candidate-mypy docs/engineering/release-policy-65/candidate_mypy.json `
  --baseline-python docs/engineering/release-policy-65/baseline_python.json `
  --candidate-python docs/engineering/release-policy-65/candidate_python.json `
  --output <review-output-directory>
```

Fetch the exact historical PR merge object if it is absent. Generation does not
infer approval or silently substitute another source SHA. Reports contain public
source/test metadata, not accounts, databases, credentials or portfolio contents.

The new evaluator and generator participate in the governance policy fingerprint.
Workflow permissions, selectors and branch rules remain unchanged.
