# Host checklist — HOST_NOT_VERIFIED

All items: HOST_VALIDATION_REQUIRED. Only versioned configuration inspected; no live host audit.

An authorized operator must record sanitized evidence of: least-privilege process account; absolute
database/data root; ACLs for data, logs, backups and temporary files; encrypted disk and independent
backup storage; available space; supported Python/runtime versions; local bind; HTTPS origin;
allowed hosts; forwarded headers accepted only from the explicitly trusted proxy; Tailscale Serve
configuration and tailnet ACL; absence of public Funnel; existing firewall policy; certificate expiry;
startup/reboot behavior; graceful stop; supervisor recovery/backoff; log rotation; process health,
readiness, backup-age alerts and disk capacity alerts.

Preconditions: separate authorization, maintenance window, validated backup, owner present, rollback plan.
Collect only metadata; never export connection strings or process environment. This PR must not invoke
tailscale serve, modify DNS/firewall/certificates, install services, restart application or change launchers.
Versioned launcher `scripts/start_income_lan.ps1` is evidence of intent, not effective host configuration.
