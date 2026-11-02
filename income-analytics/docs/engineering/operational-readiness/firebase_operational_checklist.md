# Firebase operational checklist

Local configuration/token/revocation/isolation controls are tested by the PR8 suites and PR10 fault
tests. Production requires Firebase mode and explicit absolute data root; emulator is forbidden in
production; default-deny authorization and revoked Admin token/session checks remain unchanged.
Expected project is supplied explicitly. No custom signature validation or permissive fallback added.

FIREBASE_CLOUD_NOT_VERIFIED. Cloud project identity, authorized domains, Web API restrictions,
IAM least privilege, service-account credentials, Admin initialization against real IAM, quotas,
revocation propagation, audit logs, billing and incident access require a separately authorized
operator. No real Firebase project/token/account was queried or changed. Do not classify the cloud
as verified from local mocks. Local controls may be marked FIREBASE_LOCAL_CONTROLS_VERIFIED only
after hosted Security and Operational suites succeed.
