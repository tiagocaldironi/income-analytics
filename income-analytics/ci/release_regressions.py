"""Issue 65 proposal evaluator. Never authorizes deployment or replaces current gates.

Inputs must be authenticated CI reports and reviewed policy, not caller-supplied
claims. This module is deliberately not connected to promotion while acceptance
and independent financial scope decisions are pending.
"""

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

from gate_policy import diagnostic_key


def content_digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def accepted_typing(
    root: Path, findings: list[dict], raw_exit: int, *, versions: dict, today: date
) -> dict:
    """Enforce the human-accepted typing inventory inside the existing quality job.

    This is an additional conjunction with the legacy check, not a replacement.
    Financial/test exceptions and production authorization are explicitly absent.
    """
    policy = json.loads((root / "ci/typing-baseline-acceptance.json").read_bytes())
    if (
        policy.get("scope") != "MYPY_OCCURRENCES_ONLY"
        or policy.get("accepted") is not True
        or not policy.get("approval_source")
        or not policy.get("approval_text")
        or not policy.get("owner")
        or any(
            policy.get(k) is not False
            for k in ("financial_waiver", "historical_tests_waived", "production_authorized")
        )
    ):
        raise ValueError("TYPING_ACCEPTANCE_INVALID")
    if date.fromisoformat(policy["review_until"]) < today:
        raise ValueError("TYPING_ACCEPTANCE_EXPIRED")
    directory = root / "docs/engineering/release-policy-65"
    manifest_bytes = (directory / "baseline_proposal.json").read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != policy["manifest_sha256"]:
        raise ValueError("TYPING_BASELINE_MANIFEST_CHANGED")
    manifest = json.loads(manifest_bytes)
    expected_names = {
        "candidate_mypy.json",
        "candidate_python.json",
        "occurrence_risk_proposals.json",
        "policy_proposal.md",
    }
    if set(manifest["references"]) != expected_names:
        raise ValueError("TYPING_BASELINE_REFERENCE_SCOPE_CHANGED")
    for name, digest in manifest["references"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != digest:
            raise ValueError("TYPING_BASELINE_REFERENCE_CHANGED")
    reference = json.loads((directory / "candidate_mypy.json").read_bytes())
    tests = json.loads((directory / "candidate_python.json").read_bytes())
    baseline = dict(manifest["contract"], findings=reference["findings"], cases=tests["cases"])
    if (
        content_digest(baseline) != policy["baseline_content_sha256"]
        or content_digest(baseline) != manifest["baseline_content_sha256"]
    ):
        raise ValueError("TYPING_BASELINE_CONTENT_CHANGED")
    if versions != baseline["tool_versions"]:
        raise ValueError("TYPING_BASELINE_TOOL_CHANGED")
    if (
        hashlib.sha256((root / "pyproject.toml").read_bytes()).hexdigest()
        != baseline["configuration_sha256"]
    ):
        raise ValueError("TYPING_BASELINE_CONFIGURATION_CHANGED")
    reviews = json.loads((directory / "occurrence_risk_proposals.json").read_bytes())
    if (
        Counter(diagnostic_key(r["finding"]) for r in reviews)
        != Counter(map(diagnostic_key, reference["findings"]))
        or len({r["id"] for r in reviews}) != len(reviews)
        or any(
            r["risk"] not in {"LOW_PROPOSED", "MEDIUM_PROPOSED"}
            or r.get("owner_proposed") != policy["owner"]
            or r.get("review_until_proposed") != policy["review_until"]
            or not all(r.get(k) for k in ("evidence", "issue", "source_sha256"))
            for r in reviews
        )
    ):
        raise ValueError("TYPING_OCCURRENCE_REVIEW_INVALID")
    if (
        type(raw_exit) is not int
        or raw_exit not in (0, 1)
        or bool(findings) != (raw_exit == 1)
        or any(f.get("tool") != "mypy" for f in findings)
    ):
        raise ValueError("TYPING_RAW_RESULT_INVALID")
    approved = Counter(map(diagnostic_key, reference["findings"]))
    observed = Counter(map(diagnostic_key, findings))
    added, removed = observed - approved, approved - observed
    return {
        "status": "BLOCKED" if added else "PASS",
        "scope": "MYPY_OCCURRENCES_ONLY",
        "baseline_content_sha256": policy["baseline_content_sha256"],
        "raw_tool_exit_code": raw_exit,
        "observed": len(findings),
        "accepted_inventory": len(reference["findings"]),
        "added": [json.loads(k) for k in added.elements()],
        "resolved": [json.loads(k) for k in removed.elements()],
        "owner": policy["owner"],
        "review_until": policy["review_until"],
        "financial_waiver": False,
        "historical_tests_waived": False,
        "production_authorized": False,
    }


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
