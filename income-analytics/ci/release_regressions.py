"""Issue 65 proposal evaluator. Never authorizes deployment or replaces current gates.

Inputs must be authenticated CI reports and reviewed policy, not caller-supplied
claims. This module is deliberately not connected to promotion while acceptance
and independent financial scope decisions are pending.
"""

import hashlib
import json
from collections import Counter

from gate_policy import diagnostic_key


def content_digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def assess(baseline: dict, candidate: dict, policy: dict, *, today: str) -> dict:
    """Require exact occurrences, full test coverage and separate critical gates.

    Line relocations require a separately reviewed, versioned baseline update;
    matching message totals or silently ignoring locations is never sufficient.
    Acceptance records are proposals until independently reviewed in GitHub.
    """
    reasons = []
    if policy.get("accepted_baseline_sha256") != content_digest(baseline):
        reasons.append("BASELINE_NOT_ACCEPTED")
    if not policy.get("approval_url") or not policy.get("approver"):
        reasons.append("HUMAN_ACCEPTANCE_MISSING")
    if policy.get("review_until", "") < today:
        reasons.append("ACCEPTANCE_EXPIRED")
    for field in ("tool_versions", "configuration_sha256", "scope"):
        if not baseline.get(field) or baseline.get(field) != candidate.get(field):
            reasons.append("EXECUTION_CONTRACT_CHANGED:" + field)
    expected = Counter(map(diagnostic_key, baseline["findings"]))
    observed = Counter(map(diagnostic_key, candidate["findings"]))
    new = observed - expected
    if new:
        reasons.append("NEW_DIAGNOSTICS")
    old_cases = {(c["class"], c["name"]): c["status"] for c in baseline["cases"]}
    current_cases = {(c["class"], c["name"]): c["status"] for c in candidate["cases"]}
    if len(current_cases) != len(candidate["cases"]):
        reasons.append("DUPLICATE_TEST_IDENTITIES")
    for identity, status in old_cases.items():
        current = current_cases.get(identity)
        if current is None or (current != "passed" and current != status):
            reasons.append("TEST_REGRESSION_OR_COVERAGE_LOSS:" + "::".join(identity))
    for identity in current_cases.keys() - old_cases.keys():
        if current_cases[identity] != "passed":
            reasons.append("NEW_TEST_NOT_PASSED:" + "::".join(identity))
    for finding in candidate["findings"]:
        review = policy.get("occurrences", {}).get(diagnostic_key(finding), {})
        if (
            review.get("risk") not in {"low", "medium"}
            or review.get("financial_impact") != "NONCRITICAL_REVIEWED"
            or review.get("security_impact") != "NONCRITICAL_REVIEWED"
            or not review.get("issue")
            or not review.get("owner")
            or not review.get("evidence")
            or review.get("review_until", "") < today
        ):
            reasons.append("UNACCEPTED_OR_CRITICAL_DIAGNOSTIC:" + diagnostic_key(finding))
    for identity, status in current_cases.items():
        if status != "passed":
            review = policy.get("tests", {}).get("::".join(identity), {})
            if (
                review.get("status") != status
                or review.get("risk") not in {"low", "medium"}
                or not review.get("issue")
                or not review.get("owner")
                or not review.get("evidence")
                or review.get("review_until", "") < today
                or review.get("financial_impact") != "NONCRITICAL_REVIEWED"
                or review.get("security_impact") != "NONCRITICAL_REVIEWED"
            ):
                reasons.append("UNACCEPTED_TEST:" + "::".join(identity))
    engineering = "BLOCKED" if reasons else "PASS"
    gates = {"Engineering": engineering}
    for gate in ("Financial", "Security", "Release"):
        # NOT_APPLICABLE requires a separate formal scope procedure, not a flag.
        gates[gate] = (
            "PASS" if candidate.get("critical_gates", {}).get(gate) == "PASS" else "BLOCKED"
        )
    return {
        "mode": "PROPOSAL_ONLY",
        "gates": gates,
        "reasons": reasons,
        "new_diagnostics": [json.loads(k) for k in new.elements()],
        "resolved_diagnostics": [json.loads(k) for k in (expected - observed).elements()],
        "deployment_authorized": False,
    }
