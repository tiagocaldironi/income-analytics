# PR10 — Operational readiness and disaster recovery

This is a versioned evidence snapshot, not a claim of postmerge validation. The definitive closure
state, final develop SHA, exact final source and postmerge CI/delivery identities are recorded in
the [PR #55 receipt](https://github.com/tiagocaldironi/income-analytics/pull/55) only after verification.
Engineering readiness and real host certification remain separate.

## Verified scope

Premerge source `a9b1980ab1d220bf38370b1f68a1c9f93004d8a8`, effective synthetic checkout
`b9e4b033a8f25e0fe8cde40fde5e326ea49921be`, run
[41045768631](https://github.com/tiagocaldironi/income-analytics/actions/runs/41045768631):
Engineering 1332, Security 137, Operational 58, frontend 31 suites, Build, Runtime, quality and
disposable staging passed. All artifacts, transport digests, package manifest, SBOM, policy and
source fingerprint were independently compared with the actual Git blobs. Global workflow failure
remains explicit because financial certification and historical quality diagnostics remain blocked.
Final-source local controls: 64 operational tests and 129 focused recovery/security tests passed,
without failures, errors or skips. Their dirty-worktree proof is distinct from hosted SHA evidence.

Baseline develop `450ff76671a89320d1bb411997d2faeb0efb590c` and PR9 #54 were verified.
Ruleset 26078982 stays active without bypass; Engineering requires Security and the new Operational
job. The original local source/worktrees are preserved. No financial calculations, certified fixtures,
manifests, expected hashes, migrations, dependency locks or productive launchers changed. The one
security timestamp test now uses synthetic UTC midnight on its local reference day, avoiding a proved
local/UTC midnight mismatch without changing the financial clock or production behavior.

## Controls and recovery

Minimal liveness and read-only readiness avoid portfolio loading. Restricted metrics and allowlisted,
PR8-sanitized lifecycle/auth/import/provider events contain no user or financial payloads. Local
dependency latency is aggregated without user/ticker labels. No external telemetry was activated.
BRAPI batch transport preserves existing timeout/one-attempt behavior and strict UTF-8 JSON, rejects
unexpected schema and never fabricates missing quotes. Other source adapters retain existing contracts.

PR7 online backup includes committed WAL. The completed snapshot owns its semantic signature even
under concurrent commits. Backup publication and restore use validated owned partial files and atomic
replacement; failed restore preserves prior semantic state. SQLite, not application unlinking, retires
quiescent WAL/SHM; live connections block replacement. Exact schema and complete synthetic state are
validated. Retention is parameterized, exact per daily/weekly/monthly bucket limits, dry-run only.
Eight runbooks and 25 required failure exercises are versioned. The gate validates inventory evidence,
runbooks and failure/beta matrices; missing, malformed, failed, skipped or inconsistent evidence cannot pass.

The named hosted database exercise recovered all 100 committed synthetic rows with zero rows lost.
Backup/restore/detection/validation timings and graceful stop are in rpo_rto_measurements.json.
Final source additionally measures application rollback decision to healthy/static/semantic validation.
These bounded synthetic measurements do not certify real host RPO/RTO; <=24h/<=2h remain proposed goals.

## Failure history and limits

First hosted run 40978579934 failed staging with GRACEFUL_STOP_FAILED after healthy installation,
backup and restore. Promotion was correctly blocked. Local reproduction stopped normally in 1.329s;
the exact original cause is NOT_PROVEN because stderr had been discarded. The disposable executor now
retains private diagnostics until cleanup, distinguishes timeout/nonzero exit and measures shutdown.
A bounded 30-second stop window replaces 10 seconds; forced or nonzero normal shutdown still fails.
The later named staging passed, including rollback, negative startup/health, schema block and cleanup.
The initial failure is retained in operational_hosted_validation.json, not hidden as an overall success.

SPOFs: one host/process/disk, identity/network dependencies and manually operated startup. The versioned
LAN helper binds all interfaces; actual proxy/Tailscale/HTTPS/firewall/supervisor state is not certified.
Local auto-migration and its legacy copy2 are unchanged and are not a WAL-safe DR procedure; controlled
DR uses the PR7/10 online snapshot mechanism. Read-only SQLite probes never mutate financial records,
but SQLite may manage WAL coordination sidecars; no unconditional sidecar deletion is implemented.

## Beta and remaining authorization

HOST_NOT_VERIFIED; FIREBASE_CLOUD_NOT_VERIFIED; FINANCIAL_CERTIFICATION_BLOCKED;
BETA_NOT_AUTHORIZED; PRODUCTION_NOT_AUTHORIZED. Firebase local controls are exercised through the
mandatory Security/Operational suites; no real Firebase project, credentials or users were queried/changed.
Beta matrix: 4 READY engineering criteria, 4 NOT_READY and 4 NOT_VERIFIED. These are scoped criteria,
not beta authorization. Financial results remain 104 passed /15 failed /9 errors /0 skips; original
case outcomes and CERT_48 remain unchanged, including the executed frozen-engine failure.

Concrete prerequisites: independent financial evidence/approval; separately authorized Windows,
Tailscale and Firebase cloud validation; approved encrypted off-host backups, keys, schedule and
retention; supervisor/freshness/disk alerts; real-host recovery drill; privacy/product acceptance and
explicit beta authorization. No production deploy/restart/migration/restore, credential rotation,
DNS/firewall/certificate change, real backup deletion or full LGPD/pentest certification is claimed.

All 14 required deliverables are in this directory. The hosted snapshot identifies its exact premerge
revision; the PR receipt and immutable postmerge Actions artifacts complete final evidence without
recursive documentation commits that would continually invalidate the SHA being documented.
