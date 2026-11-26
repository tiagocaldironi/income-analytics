"""Fail-closed eligibility checks used by the local Windows production executor."""

from __future__ import annotations

import re
import hashlib


def evaluate(candidate: dict, staging: dict, scope: dict, authorization: dict) -> dict:
    """Check that independent, immutable evidence agrees on one exact artifact."""
    blockers: list[str] = []
    commit = candidate.get("source_commit")
    digest = candidate.get("package_sha256")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        blockers.append("SOURCE_COMMIT_INVALID")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        blockers.append("PACKAGE_DIGEST_INVALID")
    for field in ("artifact_id", "build_run_id", "build_run_attempt"):
        if not candidate.get(field):
            blockers.append("PROVENANCE_" + field.upper() + "_MISSING")
    if staging.get("status") != "PASS" or staging.get("staging_status") != "STAGING_VALIDATED":
        blockers.append("STAGING_NOT_VALIDATED")
    staged = staging.get("candidate", {})
    if staged.get("source_commit") != commit or staged.get("package_sha256") != digest:
        blockers.append("STAGING_ARTIFACT_MISMATCH")
    for field in ("artifact_id", "build_run_id", "build_run_attempt"):
        if staged.get(field) != candidate.get(field):
            blockers.append("STAGING_PROVENANCE_" + field.upper() + "_MISMATCH")
    if scope.get("checkout_sha") != commit:
        blockers.append("SCOPE_COMMIT_MISMATCH")
    if staging.get("workflow_identity", {}).get("controller_checkout_sha") != commit:
        blockers.append("STAGING_CONTROLLER_COMMIT_MISMATCH")
    checks = staging.get("checks", {})
    required_checks = {
        "known_good_A", "installation", "health", "backup", "restore", "rollback",
        "rollback_restore", "synthetic_restore_after_block", "immutable_promotion", "cleanup",
    }
    for name in sorted(required_checks):
        if checks.get(name, {}).get("status") != "PASS":
            blockers.append("STAGING_CHECK_" + name.upper() + "_NOT_PASS")
    for name in ("negative_restore_changed_state", "negative_health", "negative_startup"):
        if checks.get(name, {}).get("status") != "EXPECTED_FAILURE_OBSERVED":
            blockers.append("STAGING_FAULT_TEST_" + name.upper() + "_MISSING")
    scope_hash = scope.get("control_applicability", {}).get("policy_sha256")
    if scope.get("decision") != "GO":
        blockers.append("SCOPED_RELEASE_NOT_GO")
    controls = scope.get("control_applicability", {}).get("controls", {})
    if not controls or any(state not in {"PASS", "NOT_APPLICABLE"} for state in controls.values()):
        blockers.append("APPLICABLE_CONTROL_BLOCKED_OR_UNKNOWN")
    if scope.get("deployment_authorized") is not False:
        blockers.append("SCOPED_REPORT_MUST_NOT_SELF_AUTHORIZE_DEPLOYMENT")
    approval = authorization.get("approval", {})
    for key, expected in (("source_commit", commit), ("package_sha256", digest),
                          ("policy_sha256", scope_hash),
                          ("artifact_id", candidate.get("artifact_id")),
                          ("build_run_id", candidate.get("build_run_id")),
                          ("staging_run_id", staging.get("workflow_identity", {}).get("delivery_run_id"))):
        if approval.get(key) != expected:
            blockers.append("PRODUCTION_APPROVAL_" + key.upper() + "_MISMATCH")
    if approval.get("state") != "APPROVED" or not approval.get("comment_id"):
        blockers.append("EXPLICIT_PRODUCTION_APPROVAL_MISSING")
    return {
        "schema": 1,
        "decision": "ELIGIBLE" if not blockers else "BLOCKED",
        "blockers": sorted(set(blockers)),
        "source_commit": commit,
        "package_sha256": digest,
        "artifact_id": candidate.get("artifact_id"),
        "policy_sha256": scope_hash,
        "staging_run_id": staging.get("workflow_identity", {}).get("delivery_run_id"),
        "deployment_authorized": False,
    }


def valid_production_comment(approval: dict, comment: dict, authority: str) -> bool:
    """Verify approval text against the fetched immutable GitHub comment object."""
    body = comment.get("body", "")
    return bool(
        approval.get("state") == "APPROVED"
        and approval.get("approver") == authority
        and comment.get("id") == approval.get("comment_id")
        and comment.get("user", {}).get("login") == authority
        and comment.get("html_url") == approval.get("comment_url")
        and hashlib.sha256(body.encode()).hexdigest() == approval.get("comment_body_sha256")
        and "PRODUCTION_ARTIFACT_APPROVED" in body
        and approval.get("source_commit") in body
        and approval.get("package_sha256") in body
        and approval.get("policy_sha256") in body
        and str(approval.get("artifact_id")) in body
    )


def require_publish_confirmation(commit: str, digest: str, entered: str) -> None:
    expected = f"DEPLOY {commit} {digest}"
    if entered != expected:
        raise ValueError("EXPLICIT_ARTIFACT_CONFIRMATION_MISMATCH")
