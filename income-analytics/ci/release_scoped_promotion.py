"""Add per-control applicability to the existing scoped promotion evaluator."""

import json
import os
import re

import scoped_promotion
from delivery_pipeline import Github
from release_applicability import evaluate as evaluate_applicability
from release_applicability import policy_digest, valid_policy_approval
from release_dependency_analysis import analyze_changed_dependencies, analyze_runtime_dependency

_ORIGINAL_EVALUATE = scoped_promotion.evaluate
APPLICABILITY_POLICY = "ci/release-applicability-policy.json"
APPLICABILITY_APPROVAL = "ci/release-applicability-approval.json"


def apply_applicability(result: dict, applicability: dict) -> dict:
    """Apply the release applicability decision without changing legacy gate logic."""
    result["control_applicability"] = applicability
    if applicability.get("decision") != "ELIGIBLE":
        result["blockers"] = sorted(
            set(result.get("blockers", []))
            | {"RELEASE_APPLICABILITY_NOT_APPROVED_OR_NOT_ELIGIBLE"}
        )
        result.setdefault("gates", {})["RELEASE"] = "BLOCKED"
        result["decision"] = "NO_GO"
    return result


def _changed_paths(client: Github, pull_request: str) -> tuple[list[str], str]:
    pr = client.json(f"pulls/{pull_request}")
    base_sha = pr.get("base", {}).get("sha", "")
    paths = []
    for page in range(1, 11):
        rows = client.json(f"pulls/{pull_request}/files?per_page=100&page={page}")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("PULL_REQUEST_FILE_LIST_INVALID")
        if any(not isinstance(row.get("filename"), str) for row in rows):
            raise ValueError("PULL_REQUEST_FILE_LIST_INVALID")
        paths.extend(row["filename"] for row in rows)
        if len(rows) < 100:
            if not re.fullmatch(r"[0-9a-f]{40}", base_sha):
                raise ValueError("PULL_REQUEST_BASE_SHA_INVALID")
            return paths, base_sha
    raise ValueError("PULL_REQUEST_FILE_LIST_INCOMPLETE")


def _historical_result(financial: dict, codes: set[str]) -> dict:
    relevant = sorted(set(financial.get("blockers", [])).intersection(codes))
    if relevant:
        return {"status": "BLOCKED", "evidence": relevant}
    state = financial.get("financial_state")
    if state == "FINANCIAL_PASS":
        return {"status": "PASS", "evidence": ["financial_state=FINANCIAL_PASS"]}
    if state == "FINANCIAL_FAIL":
        return {"status": "FAIL", "evidence": financial.get("unexpected_failures", [])}
    return {
        "status": "BLOCKED",
        "evidence": sorted(financial.get("blockers", [])) or [f"financial_state={state}"],
    }


def _with_applicability(changed_paths: list[str], base_sha: str, client: Github):
    def evaluate(root, reports, security, staging, gate, comment, record, identity, surfaces):
        policy_path = root / APPLICABILITY_POLICY
        approval_record = json.loads(
            (root / APPLICABILITY_APPROVAL).read_text(encoding="utf-8")
        )
        approval = approval_record.get("approval", {})
        policy_comment = (
            client.json("issues/comments/" + str(approval["comment_id"]))
            if approval.get("state") == "APPROVED"
            else {}
        )
        financial = reports["financial"]
        scoped = financial.get("scoped_release_assessment", {})
        static_dependencies = analyze_changed_dependencies(root, changed_paths)
        runtime_dependencies = analyze_runtime_dependency(root, changed_paths, base_sha)
        policy_approved = valid_policy_approval(policy_path, approval_record, policy_comment)
        controls = {
            "CERT_48": _historical_result(
                financial,
                {"CERT_48_REQUIRES_INDEPENDENT_RECONCILIATION", "FROZEN_IDENTITY_MISMATCH"},
            ),
            "IDENTITY_PROVENANCE_UNAPPROVED": _historical_result(
                financial,
                {
                    "IDENTITY_PROVENANCE_UNAPPROVED",
                    "HISTORICAL_PROVENANCE_INCOMPLETE",
                    "FROZEN_IDENTITY_MISMATCH",
                },
            ),
            "22_HISTORICAL_REFERENCES_UNAPPROVED": _historical_result(
                financial,
                {"22_HISTORICAL_REFERENCES_UNAPPROVED", "HISTORICAL_PROVENANCE_INCOMPLETE"},
            ),
            "CORE_FINANCIAL_REGRESSION": {
                "status": "PASS" if scoped.get("technical_state") == "PASS" else "BLOCKED",
                "evidence": {
                    "technical_state": scoped.get("technical_state"),
                    "totals": scoped.get("scoped_totals"),
                    "checkout_sha": scoped.get("checkout_sha"),
                },
            },
            "SECURITY": {
                "status": "PASS" if security.get("status") == "PASS" else "FAIL",
                "evidence": {"status": security.get("status")},
            },
            "BUILD": {
                "status": "PASS" if reports["build"].get("exit_code") == 0 else "FAIL",
                "evidence": {
                    "exit_code": reports["build"].get("exit_code"),
                    "artifact_sha256": reports["build"].get("artifact_sha256"),
                },
            },
            "STAGING": {
                "status": "PASS" if identity.get("staging_job") == "success" else "FAIL",
                "evidence": {
                    "job_result": identity.get("staging_job"),
                    "candidate_sha256": staging.get("candidate", {}).get("package_sha256"),
                },
            },
            "RUNTIME_DEPENDENCY": {
                "status": runtime_dependencies.get("status", "BLOCKED"),
                "evidence": runtime_dependencies,
            },
            "RELEASE_POLICY_REVIEW": {
                "status": "PASS" if policy_approved else "BLOCKED",
                "evidence": {"policy_sha256": policy_digest(policy_path),
                             "approval_verified": policy_approved},
            },
            "PRODUCTION_DELIVERY": {
                "status": (
                    "PASS"
                    if reports["python"].get("exit_code") == 0
                    and reports["build"].get("exit_code") == 0
                    and security.get("status") == "PASS"
                    and identity.get("staging_job") == "success"
                    else "BLOCKED"
                ),
                "evidence": {
                    "python_exit_code": reports["python"].get("exit_code"),
                    "build_exit_code": reports["build"].get("exit_code"),
                    "security_status": security.get("status"),
                    "staging_job": identity.get("staging_job"),
                },
            },
        }
        applicability = evaluate_applicability(
            changed_paths,
            {
        "complete": (
                    scoped.get("technical_state") == "PASS"
                    and static_dependencies.get("complete") is True
                ),
                "modules": scoped.get("dependency_calls", []),
                "static_analysis": static_dependencies,
            },
            controls,
            json.loads(policy_path.read_text(encoding="utf-8")),
            approved=policy_approved,
        )
        result = _ORIGINAL_EVALUATE(
            root, reports, security, staging, gate, comment, record, identity, surfaces
        )
        return apply_applicability(result, applicability)

    return evaluate


def main() -> int:
    pull_request = os.environ.get("RELEASE_PR_NUMBER", "")
    if not re.fullmatch(r"[1-9][0-9]{0,8}", pull_request):
        raise ValueError("INVALID_RELEASE_PR_NUMBER")
    client = Github(os.getenv("RELEASE_GITHUB_TOKEN"))
    try:
        changed_paths, base_sha = _changed_paths(client, pull_request)
    except Exception:
        output = scoped_promotion.ROOT / "ci-reports/promotion"
        output.mkdir(parents=True, exist_ok=True)
        result = {
            "decision": "NO_GO",
            "blockers": ["DEPENDENCY_FILE_EVIDENCE_UNAVAILABLE"],
            "gates": {"RELEASE": "BLOCKED"},
            "merge_authorized": False,
            "deployment_authorized": False,
        }
        (output / "promotion-report.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        return 1
    original_evaluate = scoped_promotion.evaluate
    scoped_promotion.evaluate = _with_applicability(changed_paths, base_sha, client)
    try:
        return scoped_promotion.main()
    finally:
        scoped_promotion.evaluate = original_evaluate


if __name__ == "__main__":
    raise SystemExit(main())
