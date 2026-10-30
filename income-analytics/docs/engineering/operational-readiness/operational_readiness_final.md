# PR10 â€” Operational readiness and disaster recovery

Current closure: OPERATIONAL_READINESS_BLOCKED until required local/hosted checks, protected integration
and distinct postmerge evidence are verified. Engineering implementation and real host certification
are separate. HOST_NOT_VERIFIED; FINANCIAL_CERTIFICATION_BLOCKED; BETA_NOT_AUTHORIZED;
PRODUCTION_NOT_AUTHORIZED. No production process, launcher, database, migration, credentials,
Tailscale, DNS, firewall or certificate changed. No external telemetry or backup schedule activated.

Baseline develop: `450ff76671a89320d1bb411997d2faeb0efb590c`; PR9 #54 merged through active ruleset
26078982, no bypass. Baseline hosted CI 40973775071 has Engineering/Security/Build success but global
failure (financial and preexisting diagnostic debt); separate disposable delivery 40974697605 passed.
Engineering required includes Security. PR10 adds Operational as a separate job required by Engineering;
no ruleset change. Local dirty source and existing worktrees remain preserved.

Controls: minimal health without portfolio loading; local allowlisted operational signals; restricted
metrics; bounded provider transport; PR7 online WAL snapshot and atomic validated restore; dry-run
parameterized retention; fail-closed operational gate; 25 named fault exercises, additional recovery,
gate and metric tests; eight incident runbooks. See inventory and contracts in this directory.

SPOFs: one host/process/disk, local data, identity/network dependency, manually operated launcher,
no certified real supervisor, encrypted off-host backup, freshness alerts or real RPO/RTO drill.
Legacy local auto-migration and preupgrade copy2 are not a WAL-safe DR procedure; unchanged here
to avoid productive launch behavior changes. Canonical controlled DR uses the PR7/10 online API.

Evidence: operational_gate_validation.json, operational_hosted_validation.json,
disaster_recovery_report.json, rpo_rto_measurements.json and beta_readiness_matrix.csv.
Hosted snapshot documents are evidence of the explicitly named revision, not future/self-referential
commits. Definitive final source and integrated/postmerge identities must be recorded separately in
the PR receipt and final response. A premerge synthetic checkout never certifies a postmerge run.

Remaining beta prerequisites: financial independent closure; authorized host/cloud validation;
approved encrypted independent backups, schedule and retention; supervisor/alerting; privacy policy,
product acceptance and explicit beta authorization. No pentest or complete LGPD compliance claimed.

Local validation: Operational 52/0/0/0; focused recovery/PR7/security timestamp 117/0/0/0. Financial 104 passed, 15 failed, 9 errors, zero skips (unchanged). Local measurements are from a dirty implementation worktree and are not hosted commit evidence. The security timestamp roundtrip test now uses synthetic UTC midnight on the local reference date; this removes a proved local/UTC midnight mismatch without changing application logic or certified tests.
