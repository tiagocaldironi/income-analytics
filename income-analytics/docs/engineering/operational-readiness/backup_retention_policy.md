# Proposed beta backup policy — NOT ACTIVATED

Proposed: daily backup; 7 daily, 4 weekly and 3 monthly restore points; periodic verified restore.
`ci/operational.py::retention_plan` validates owned paths, hash, integrity, exact schema and semantic
signature before a dry-run plan; settings are bounded and configurable. Newest valid copy always retained.
Daily/week/month buckets use UTC. Corrupt, future-dated or invalid records fail the plan.
There is no deletion function, scheduler, real backup scan or cloud synchronization.

Reuse PR7 SQLite online backup API, including committed WAL, and validate the completed snapshot.
A fixed owned .partial path prevents collision; publication uses same-directory atomic replace.
Restore checks hash, schema, exact synthetic semantics and stopped disposable processes before writing
an alternate file, validates it, then atomically replaces the destination. Active WAL connections prohibit
replacement. For quiescent sidecars SQLite must acquire exclusivity and transition to DELETE mode;
the application never unlinks WAL/SHM. Failure preserves prior semantic state and cleans owned partial files.
Use a private directory ACL and encrypted-at-rest storage independent of the application disk for beta.
Encryption keys and off-host storage are NOT provisioned or certified here. Same-disk snapshots alone
do not protect against host/disk loss. Snapshots contain sensitive data in a real deployment.

Pending approval: storage location/budget; encryption mechanism and key recovery; operator access;
off-host copy; retention/legal basis; daily schedule; restore drill cadence; alert routing. Proposed
RPO <=24h and RTO <=2h are engineering goals, not achieved host guarantees. No production policy changed.
