# Local observability

PR8 `security_logging.redact` is reused. Operational records admit only a fixed event enum,
UTC timestamp, severity, operations component, generated random request/event ID and bounded duration.
No arbitrary fields, source URLs, supplied request IDs, payloads, users, portfolios, tickers, cookies,
bearer credentials, imports or financial values are admitted. No remote telemetry is installed.

Process-local metrics: uptime/process_up; request count; HTTP 5xx count/rate; aggregate mean latency;
401/403; import failures; provider failures. No high-cardinality labels or raw URL logging.
The restricted status endpoint exposes a JSON collection interface. Counters reset on restart;
they are not a durable audit ledger. Health transitions log only on change. Request successes are
counted, not individually logged. Authentication failure events carry no identity.

Backup duration/timestamp, restore validation duration, recovery outcome and latest valid snapshot age
are recorded in disposable recovery receipts. They are not falsely reported as real host backup age.
Real backup freshness alerts, protected log sink/rotation and supervisor checks require host validation.
Legacy financial diagnostic logs are outside the new allowlist and remain subject to PR8 redaction;
do not enable verbose legacy profiling in beta without reviewing its fields.

Minimum event IDs exist in `operational.EVENTS`; actual lifecycle/readiness/auth/import/batch-provider
paths are wired. Backup/restore events belong to the disposable recovery wrapper. Startup failure before
app import and abrupt termination require the future supervisor. A collector exception fails open for
the financial request with a fixed monitoring-failed code, never its raw exception text.

Disposable delivery now emits allowlisted backup start/complete/failure and restore validation failure records without exception payloads. Provider attempts expose aggregate dependency latency. Child diagnostics are retained only inside the owned temporary workspace and never uploaded; cleanup removes them. Shutdown errors distinguish timeout from nonzero exit, and successful staging records measured stop duration and exit status.
