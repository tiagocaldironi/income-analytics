# Incident runbooks

Owner for all incidents: designated maintainer; security/privacy owner for INC-06. No external messages are sent automatically.

## INC-01 — Application unavailable

- Symptoms/detection: health/live timeout or readiness 503.
- Severity: critical; owner: designated maintainer, escalation to security/privacy owner as required.
- First actions/diagnosis: Identify process/supervisor health and last approved deployment; do not restart production automatically.
- Containment: Preserve sanitized lifecycle metadata; isolate traffic under operator approval.
- Recovery: Restore last verified immutable package after host authorization; verify live, ready and synthetic smoke.
- Verification: health and exact artifact/schema identity; synthetic semantic checks; no cross-user disclosure.
- Closure: service stable, cause recorded, backup/rollback evidence validated and owner signs off.
- Evidence: UTC timeline, commit/run IDs, stable error codes and sanitized counters; never financial payloads.
- Communication: maintainer records impact/time window and next update; user/legal notification is a human decision.

## INC-02 — SQLite unavailable or corrupt

- Symptoms/detection: 503 or integrity/lock error.
- Severity: critical; owner: designated maintainer, escalation to security/privacy owner as required.
- First actions/diagnosis: Preserve database and WAL/SHM as a consistent set; do not delete files or run repair tools.
- Containment: Check path/ACL/space/lock ownership using approved host procedures; do not migrate.
- Recovery: Stop authorized writer, choose validated backup, restore in alternate directory and verify schema plus semantics before switching.
- Verification: health and exact artifact/schema identity; synthetic semantic checks; no cross-user disclosure.
- Closure: service stable, cause recorded, backup/rollback evidence validated and owner signs off.
- Evidence: UTC timeline, commit/run IDs, stable error codes and sanitized counters; never financial payloads.
- Communication: maintainer records impact/time window and next update; user/legal notification is a human decision.

## INC-03 — Firebase authentication failure

- Symptoms/detection: aggregate 401 increase.
- Severity: high; owner: designated maintainer, escalation to security/privacy owner as required.
- First actions/diagnosis: Check project/origin/time and provider status without copying tokens.
- Containment: Do not disable authentication/revocation/CSRF or ownership enforcement.
- Recovery: Authorized identity operator restores configuration; test revoked token denial and separate-user access.
- Verification: health and exact artifact/schema identity; synthetic semantic checks; no cross-user disclosure.
- Closure: service stable, cause recorded, backup/rollback evidence validated and owner signs off.
- Evidence: UTC timeline, commit/run IDs, stable error codes and sanitized counters; never financial payloads.
- Communication: maintainer records impact/time window and next update; user/legal notification is a human decision.

## INC-04 — External source unavailable

- Symptoms/detection: provider errors, timeout or 429.
- Severity: medium; owner: designated maintainer, escalation to security/privacy owner as required.
- First actions/diagnosis: Identify source and effective date from sanitized status; honor quota.
- Containment: Bound retries; label stale observations; never replace missing data with zero or fabricated prices.
- Recovery: Recover provider under approved contract; verify source/date and no financial writes from failed attempt.
- Verification: health and exact artifact/schema identity; synthetic semantic checks; no cross-user disclosure.
- Closure: service stable, cause recorded, backup/rollback evidence validated and owner signs off.
- Evidence: UTC timeline, commit/run IDs, stable error codes and sanitized counters; never financial payloads.
- Communication: maintainer records impact/time window and next update; user/legal notification is a human decision.

## INC-05 — Import failure

- Symptoms/detection: aggregate import errors.
- Severity: high; owner: designated maintainer, escalation to security/privacy owner as required.
- First actions/diagnosis: Isolate failed synthetic/real batch; retain only approved evidence; no financial payload in logs.
- Containment: Do not blindly replay partial operations; inspect idempotency and original input privately.
- Recovery: Reconcile transaction outcome, retest a synthetic batch, then obtain authorization for real retry.
- Verification: health and exact artifact/schema identity; synthetic semantic checks; no cross-user disclosure.
- Closure: service stable, cause recorded, backup/rollback evidence validated and owner signs off.
- Evidence: UTC timeline, commit/run IDs, stable error codes and sanitized counters; never financial payloads.
- Communication: maintainer records impact/time window and next update; user/legal notification is a human decision.

## INC-06 — Suspected data disclosure

- Symptoms/detection: secret scanner, unauthorized access or privacy report.
- Severity: critical; owner: designated maintainer, escalation to security/privacy owner as required.
- First actions/diagnosis: Restrict access using an authorized incident owner; preserve evidence and chain of custody.
- Containment: No tokens or payloads in tickets; no unapproved data deletion or secret rotation.
- Recovery: Security owner coordinates credential actions, forensic review, legal/privacy notification and verification.
- Verification: health and exact artifact/schema identity; synthetic semantic checks; no cross-user disclosure.
- Closure: service stable, cause recorded, backup/rollback evidence validated and owner signs off.
- Evidence: UTC timeline, commit/run IDs, stable error codes and sanitized counters; never financial payloads.
- Communication: maintainer records impact/time window and next update; user/legal notification is a human decision.

## INC-07 — Failed deployment

- Symptoms/detection: artifact/health/staging failure.
- Severity: critical; owner: designated maintainer, escalation to security/privacy owner as required.
- First actions/diagnosis: Block promotion and compare exact artifact digest, source SHA and schema contract.
- Containment: No unverified rebuild/downgrade; retain previous immutable package and database.
- Recovery: Use PR7 approved rollback; if schema differs require explicit restore plan; verify semantic synthetic state.
- Verification: health and exact artifact/schema identity; synthetic semantic checks; no cross-user disclosure.
- Closure: service stable, cause recorded, backup/rollback evidence validated and owner signs off.
- Evidence: UTC timeline, commit/run IDs, stable error codes and sanitized counters; never financial payloads.
- Communication: maintainer records impact/time window and next update; user/legal notification is a human decision.

## INC-08 — Invalid backup

- Symptoms/detection: hash, manifest, integrity or restore failure.
- Severity: high; owner: designated maintainer, escalation to security/privacy owner as required.
- First actions/diagnosis: Quarantine invalid copy without deleting other backups; record stable error code.
- Containment: Never restore an unvalidated copy; suspend retention deletion.
- Recovery: Select independently validated restore point, exercise alternate-path restore and review missed RPO.
- Verification: health and exact artifact/schema identity; synthetic semantic checks; no cross-user disclosure.
- Closure: service stable, cause recorded, backup/rollback evidence validated and owner signs off.
- Evidence: UTC timeline, commit/run IDs, stable error codes and sanitized counters; never financial payloads.
- Communication: maintainer records impact/time window and next update; user/legal notification is a human decision.
