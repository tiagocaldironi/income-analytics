# CI recovery: bounded diagnosis, no gate bypass

## Situation (2026-11-18)

A documentation-only PR (#83) ran the full Windows CI matrix. The run reported
financial tests 190 passed / 15 failed / 9 errors, and full Python tests
1630 passed / 15 failed / 9 errors. Security emitted
`{"status":"FAIL","failures":[]}`; this is **not** proof of a clean scan:
the `failures` field records scanner exceptions, while individual gate statuses
are stored in `ci-reports/security/result.json`.

The engineering summary also reported `FROZEN_IDENTITY_MISMATCH`. Do not
attribute these failures to PR #83 until a baseline run on `develop` confirms
the difference.

## Operating policy

1. Stop unbounded retry / poll loops. One CI inspection per candidate SHA is
   enough for diagnosis; rerun only after a relevant code or configuration change.
2. Record each failure with exact check, first failing assertion, candidate SHA,
   baseline SHA, and whether it reproduces on `develop`. Mark unknowns unknown.
3. Preserve the original results, full financial certification, security scanning,
   identity checks, and release gates. Do not use `continue-on-error`, exclusions,
   permissive baselines, fabricated approvals, or disabled branch protections.
4. Keep existing failures visible as **blocked**. Separate remediation work by
   domain; do not expand a feature PR into a repository-wide cleanup.
5. Make security failure output diagnostic but sanitized: gate names and status
   only in console; detailed evidence remains in the retained report artifact.
6. Optimize the workflow trigger strategy only after mapping required checks,
   `workflow_run` dependencies, and policy fingerprint coupling. A docs-only
   fast path must not make required checks silently disappear or permit releases
   without the existing controls.

## Exit criteria for this first recovery PR

- Security CLI prints fixed-name gate states and failing gate names.
- Security `FAIL` remains a nonzero exit code; scanner errors remain fail-closed.
- No CI gate, financial calculation, approval, release rule, or dependency changed.
- PR may remain blocked by historical failures; report them once and stop.
- Follow-up: baseline comparison and independently reviewed, risk-based CI split.
