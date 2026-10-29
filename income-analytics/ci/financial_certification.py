"""Fail-closed evidence controls; no financial calculation or baseline generation."""

import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "ci/financial_certification_policy.json"


def failure_causes(raw_junit: Path) -> dict[str, str]:
    """Emit only enum codes; never persist traceback payloads or personal paths."""
    if raw_junit.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("JUNIT_SIZE_LIMIT")
    payload = raw_junit.read_bytes().decode("utf-8")
    if "\x00" in payload or "<!DOCTYPE" in payload.upper() or "<!ENTITY" in payload.upper():
        raise ValueError("JUNIT_UNSAFE_XML")
    causes = {}
    for case in ET.fromstring(payload).iter("testcase"):
        node = case.get("classname", "").replace(".", "/") + ".py::" + case.get("name", "")
        problem = next((child for child in case if child.tag in {"failure", "error"}), None)
        if problem is None:
            continue
        text = (problem.get("message", "") + "\n" + (problem.text or "")).replace("\\", "/")
        code = "UNCLASSIFIED_FAILURE"
        if "FileNotFoundError:" in text and any(
            name in text
            for name in (
                "ranking_snapshot.json",
                "methodological_universe.csv",
                "methodological_universe_v8.csv",
            )
        ):
            code = "MISSING_HISTORICAL_FILE"
        elif (
            "sqlite3.OperationalError: unable to open database file" in text
            and "magic_formula_universe_repository.py" in text
        ):
            code = "MISSING_HISTORICAL_DATABASE"
        elif "AssertionError" in text and "hashlib.sha256" in text:
            code = "FROZEN_IDENTITY_MISMATCH"
        causes[node] = code
    return causes


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def validate_evidence(payload: bytes, requirement: dict, approval: dict) -> list[str]:
    """Compare against independently supplied pins, never hashes from the payload itself.

    A digest proves integrity only. The separately reviewed authority pin must bind
    source, engine, policy, period and expected result to the exact original bytes.
    Production currently has no such approval for its pending historical evidence.
    """
    problems = []
    digest = sha256(payload)
    if digest != requirement.get("sha256"):
        problems.append("EVIDENCE_DIGEST_MISMATCH")
    if (
        approval.get("origin") != "INDEPENDENT_ORIGINAL"
        or not requirement.get("approval_authority")
        or approval.get("authority") != requirement.get("approval_authority")
        or not requirement.get("approval_record")
        or approval.get("record") != requirement.get("approval_record")
        or approval.get("sha256") != digest
        or approval.get("record_sha256") != requirement.get("approval_record_sha256")
        or not approval.get("record_sha256")
    ):
        problems.append("INDEPENDENT_PROVENANCE_MISSING")
    try:
        document = json.loads(payload)
        if not isinstance(document, dict):
            raise ValueError("INVALID_EVIDENCE")
        for key in ("snapshot_id", "engine_version", "policy_id", "period", "source_id"):
            if not requirement.get(key) or document.get(key) != requirement[key]:
                problems.append(key.upper() + "_MISMATCH")
        if document.get("generator") == "IMPLEMENTATION_UNDER_TEST":
            problems.append("SELF_GENERATED_EXPECTATION_FORBIDDEN")
        if (
            not requirement.get("expected_result_sha256")
            or document.get("expected_result_sha256") != requirement["expected_result_sha256"]
        ):
            problems.append("EXPECTED_RESULT_NOT_INDEPENDENTLY_PINNED")
        cutoff = date.fromisoformat(requirement["price_cutoff"])
        if date.fromisoformat(document["price_date"]) > cutoff:
            problems.append("FUTURE_PRICE_FOR_HISTORICAL_REFERENCE")
        if requirement.get("source_kind") not in {
            "B3_COTAHIST",
            "CVM_DFP",
            "CVM_ITR",
            "CVM_FCA",
        } or document.get("source_kind") != requirement.get("source_kind"):
            problems.append("INCOMPATIBLE_B3_CVM_SOURCE")
        order = document["canonical_order"]
        if not isinstance(order, list) or order != sorted(set(order)):
            problems.append("NONDETERMINISTIC_OR_DUPLICATE_ORDER")
    except ValueError, TypeError, KeyError:
        problems.append("EVIDENCE_SCHEMA_INVALID")
    return sorted(set(problems))


def frozen_integrity(root: Path, pins: list[dict]) -> list[dict]:
    rows = []
    for pin in pins:
        manifest = root / pin["manifest"]
        if not manifest.is_file() or sha256(manifest.read_bytes()) != pin["sha256"]:
            rows.append({"manifest": pin["manifest"], "code": "FROZEN_MANIFEST_MISMATCH"})
            continue
        document = json.loads(manifest.read_text(encoding="utf-8"))
        base = root if pin["key"] == "frozen_code_sha256" else manifest.parent
        for name, expected in document[pin["key"]].items():
            path = base / name
            observed = sha256(path.read_bytes()) if path.is_file() else None
            rows.append(
                {
                    "manifest": pin["manifest"],
                    "file": path.relative_to(root).as_posix(),
                    "expected_sha256": expected,
                    "observed_sha256": observed,
                    "code": "VERIFIED_BYTES"
                    if observed == expected
                    else "FROZEN_IDENTITY_MISMATCH",
                }
            )
    return rows


def historical_provenance(root: Path, policy: dict) -> list[dict]:
    """Original metadata cannot be replaced by deleting diagnostic blocker labels."""
    pin = policy["original_provenance_manifest"]
    path = root / pin["path"]
    if not path.is_file() or sha256(path.read_bytes()) != pin["sha256"]:
        return [{"id": "ORIGINAL_REFERENCE_MANIFEST", "state": "CONFLICTING"}]
    references = {
        row["id"]: row for row in json.loads(path.read_text(encoding="utf-8"))["references"]
    }
    expected = set(references) - {"cvm-dfp-2025-index", "synthetic-historical-replacement"}
    if set(policy["required_reference_ids"]) != expected:
        return [{"id": "REQUIRED_REFERENCE_SCOPE", "state": "CONFLICTING"}]
    rows = []
    for reference_id in policy["required_reference_ids"]:
        item = references.get(reference_id, {})
        approved = (
            item.get("state") == "VERIFIED"
            and item.get("ci_approved") is True
            and item.get("license", {}).get("state") == "VERIFIED"
            and bool(item.get("independent_evidence"))
            and bool(item.get("approval_record_sha256"))
        )
        # Existing metadata contains no independent approval record for these
        # complete historical inputs. Do not open unapproved/possibly licensed data.
        rows.append(
            {
                "id": reference_id,
                "state": "NOT_VERIFIED" if approved else "BLOCKED",
                "reason": "Complete independently approved historical source chain required",
            }
        )
    return rows


def classify_results(
    details: dict, required: set[str], known_blocked: set[str], blockers: list[str]
) -> dict:
    """Known blocked assertions remain failures; unexpected failures are FINANCIAL_FAIL."""
    cases = details.get("cases", [])
    observed = {
        row["class"].replace(".", "/") + ".py::" + row["name"]: row["status"] for row in cases
    }
    totals = details.get("totals", {})
    actual = {
        key: sum(row.get("status") == key for row in cases)
        for key in ("passed", "failed", "errors", "skipped")
    }
    invalid = (
        not cases
        or len(observed) != len(cases)
        or actual != totals
        or not required.issubset(observed)
        or any(row.get("status") not in actual for row in cases)
        or totals.get("skipped", 0) != 0
    )
    unexpected = sorted(
        node
        for node, state in observed.items()
        if state in {"failed", "errors"} and node not in known_blocked
    )
    if invalid:
        state = "FINANCIAL_NOT_VERIFIED"
    elif unexpected:
        state = "FINANCIAL_FAIL"
    elif blockers or any(actual[key] for key in ("failed", "errors")):
        state = "FINANCIAL_BLOCKED"
    else:
        state = "FINANCIAL_PASS"
    return {
        "financial_state": state,
        "unexpected_failures": unexpected,
        "mandatory_coverage_verified": not invalid,
        "release_authorized": False,
    }


def evaluate(root: Path, details: dict) -> dict:
    policy = json.loads((root / POLICY.relative_to(ROOT)).read_text(encoding="utf-8"))
    rows = frozen_integrity(root, policy["frozen_manifests"])
    historical = historical_provenance(root, policy)
    blockers = []
    if any(row["code"] != "VERIFIED_BYTES" for row in rows):
        blockers.append("FROZEN_IDENTITY_MISMATCH")
    if any(row["state"] != "VERIFIED" for row in historical):
        blockers.append("HISTORICAL_PROVENANCE_INCOMPLETE")
    # No approval can be inferred from newline equivalence, self-reported digests,
    # a newer official archive or an aggregate ranking count.
    for item in policy["unresolved_approvals"]:
        blockers.append(item["code"])
    groups = json.loads((root / "ci/test-groups.json").read_text(encoding="utf-8"))
    required = set(policy["mandatory_financial_tests"])
    required.update(groups["historical_reference_tests"] + groups["frozen_integrity_tests"])
    known = {
        node
        for node, cause in policy["known_failure_causes"].items()
        if details.get("failure_causes", {}).get(node) == cause
    }
    result = classify_results(details, required, known, blockers)
    return {
        **result,
        "blockers": sorted(set(blockers)),
        "frozen_integrity": rows,
        "historical_provenance": historical,
        "policy_sha256": sha256((root / POLICY.relative_to(ROOT)).read_bytes()),
        "provenance": "BLOCKED_NO_INDEPENDENT_APPROVAL",
        "production_authorized": False,
    }
