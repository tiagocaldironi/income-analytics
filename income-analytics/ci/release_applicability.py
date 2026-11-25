"""Fail-closed, per-control applicability for candidate releases.

This evaluator never infers approval from test outcomes. A NOT_APPLICABLE result
requires an exact policy digest approval, complete dependency evidence, and no
observed calls into the control's protected modules.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path

STATES = {"PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE"}


def policy_digest(path: Path) -> str:
    policy = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def valid_policy_approval(policy_path: Path, record: dict, comment: dict) -> bool:
    """Bind owner approval to the exact policy bytes and immutable GitHub comment."""
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    approval = record.get("approval", {})
    body = comment.get("body", "")
    digest = policy_digest(policy_path)
    approver = approval.get("approver")
    return (
        approver == policy.get("approval_authority")
        and approval.get("state") == "APPROVED"
        and approval.get("policy_sha256") == digest
        and bool(approval.get("comment_id"))
        and bool(approval.get("comment_url"))
        and bool(approval.get("comment_body_sha256"))
        and comment.get("id") == approval.get("comment_id")
        and comment.get("html_url") == approval.get("comment_url")
        and comment.get("user", {}).get("login") == approver
        and hashlib.sha256(body.encode()).hexdigest()
        == approval.get("comment_body_sha256")
        and "RELEASE_POLICY_APPROVED" in body
        and digest in body
    )


def classify_scope(paths: list[str], policy: dict) -> set[str]:
    """Classify all changed paths; an unmatched path is explicitly unknown."""
    if not paths:
        return {"unknown"}
    scopes: set[str] = set()
    for raw in paths:
        path = raw.replace("\\", "/").removeprefix("income-analytics/")
        matches = {
            scope
            for scope, patterns in policy["path_scopes"].items()
            if any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)
        }
        scopes.update(matches or {"unknown"})
    return scopes


def evaluate(
    paths: list[str],
    dependency_evidence: dict,
    control_results: dict[str, str],
    policy: dict,
    *,
    approved: bool,
) -> dict:
    scopes = classify_scope(paths, policy)
    raw_calls = dependency_evidence.get("modules", [])
    valid_calls = isinstance(raw_calls, list) and all(
        isinstance(module, str) and module.strip() for module in raw_calls
    )
    calls = raw_calls if valid_calls else []
    modules = [call.split(":", 1)[0] for call in calls]
    trace_complete = dependency_evidence.get("complete") is True and valid_calls
    controls = {}
    reasons = {}
    evidence = {}

    for name, rule in policy["controls"].items():
        if "unknown" in scopes:
            state = "BLOCKED"
            reason = "UNKNOWN_CHANGE_SCOPE"
        elif scopes.intersection(rule["applicable_scopes"]):
            observed = control_results.get(name)
            observed_state = observed.get("status") if isinstance(observed, dict) else observed
            if observed_state not in STATES or observed_state == "NOT_APPLICABLE":
                state, reason = "BLOCKED", "APPLICABLE_CONTROL_RESULT_MISSING_OR_INVALID"
            else:
                state, reason = observed_state, "CONTROL_APPLIES_TO_CHANGED_SCOPE"
                evidence[name] = observed.get("evidence", []) if isinstance(observed, dict) else []
        else:
            forbidden = rule["dependency_modules"]
            touched = sorted(
                module
                for module in modules
                if any(module == prefix or module.startswith(prefix + ".") for prefix in forbidden)
            )
            if not approved:
                state, reason = "BLOCKED", "RELEASE_POLICY_APPROVAL_REQUIRED"
            elif not trace_complete:
                state, reason = "BLOCKED", "DEPENDENCY_ANALYSIS_INCOMPLETE"
            elif touched:
                state, reason = "BLOCKED", "PROTECTED_DEPENDENCY_OBSERVED"
            else:
                state, reason = "NOT_APPLICABLE", "APPROVED_SCOPE_AND_NO_PROTECTED_DEPENDENCY"
                evidence[name] = {
                    "changed_paths": sorted(paths),
                    "dependency_modules_checked": sorted(set(modules)),
                    "policy_approval_sha256": hashlib.sha256(
                        json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
                    ).hexdigest(),
                }
        controls[name] = state
        reasons[name] = reason

    mandatory = {}
    for name in policy["mandatory_controls"]:
        observed = control_results.get(name)
        observed_state = observed.get("status") if isinstance(observed, dict) else observed
        if observed_state not in {"PASS", "FAIL", "BLOCKED"}:
            mandatory[name] = "BLOCKED"
            reasons[name] = "MANDATORY_CONTROL_RESULT_MISSING_OR_INVALID"
        else:
            mandatory[name] = observed_state
            evidence[name] = observed.get("evidence", []) if isinstance(observed, dict) else []

    all_states = [*controls.values(), *mandatory.values()]
    eligible = bool(all_states) and all(state in {"PASS", "NOT_APPLICABLE"} for state in all_states)
    return {
        "schema": 1,
        "scopes": sorted(scopes),
        "controls": {**controls, **mandatory},
        "reasons": reasons,
        "evidence": evidence,
        "dependency_evidence": {
            "complete": trace_complete,
            "modules": sorted(set(modules)),
        },
        "policy_sha256": hashlib.sha256(
            json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "decision": "ELIGIBLE" if eligible else "BLOCKED",
        "merge_authorized": False,
        "deployment_authorized": False,
    }
