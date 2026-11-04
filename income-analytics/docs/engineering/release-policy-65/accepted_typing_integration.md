# Accepted typing baseline — bounded CI enforcement

On 2026-11-03 the owner explicitly approved policy v1, then replied:
“Aceito o baseline de tipagem e o prazo propostos”. The question identified
proposal commit `c687acf`, 486 typing occurrences (397 low / 89 medium proposed),
owner `tiagocaldironi`, review date 2026-11-17 and canonical digest
`bfb56031699c3b79908657442703c086cc6f18fceea8f9c7d30abee1c177b74e`.
The approval explicitly excludes financial failures, historical tests, CERT_48,
merge and deployment. `ci/typing-baseline-acceptance.json` records this scope.

The original proposal documents/inventories remain unchanged as review artifacts;
their PENDING/NOT_ACCEPTED fields describe the earlier checkpoint. The acceptance
registry binds their exact content and supplies the later, typing-only decision.
It is a repository review record of the direct human instruction, not a claim of
an independent financial signature or GitHub review that did not occur.

## Additional conjunction in the existing quality job

No job, module, test or legacy comparison was removed. The existing full mypy
job still reports exit 1 and every finding. The existing quality job still runs
both Ruff and mypy over their full original scopes and evaluates its old ledger.
It now also invokes `accepted_typing`; **both comparisons must pass**.

This check validates the approval scope, manifest/reference digests, baseline
content, tool/Python versions, configuration digest, complete per-ID risk review,
owner and deadline, exact diagnostic identities and multiplicities. New/moved/
changed occurrences, duplicates, malformed tool results, changed references or
configuration, expired acceptance and high/unreviewed risks fail closed. Debt
resolutions may disappear; they never offset additions. Expiry is inclusive
2026-11-17 UTC. The existing lock-file validation remains required as well.

The quality report retains raw tool exit codes and adds
`accepted_typing_nonregression`: PASS means no new typing debt against the
accepted inventory, **not** that the raw mypy run is clean. Controlled public
error codes explain acceptance failures without publishing exception payloads.

The complete `assess` release-policy evaluator remains PROPOSAL_ONLY. Only the
typing-specific additional comparison is connected to CI after its approval.
No financial or historical-test waiver is implemented. Existing Engineering,
Financial, Security and Release gates and branch rules remain in force.
Production authorization remains false. CERT_48 still runs and remains blocked.

## Validation

The actual local quality job passed with all 486 findings retained and zero new
occurrences. Negative controls cover changes in rule/message/location/file,
multiplicity, tool/configuration/reference tampering, expiry, Boolean/float/crash
exit codes, forbidden financial/test/production waivers and rehashed high-risk or
incomplete occurrence reviews. Integration controls exercise the conjunction of
the old and new comparisons. Hosted evidence must refer to the resulting commit;
earlier successful engineering/rollback checkpoints are not substituted for it.
