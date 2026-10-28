"""Explicit CI scope and multiset debt policy; independent of financial code."""

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = json.loads((ROOT / "ci/test-groups.json").read_text(encoding="utf-8"))
BASELINE = ROOT / "docs/engineering/cicd-assessment/ci_quality_baseline.json"


def test_scope(nodeid: str) -> dict:
    file = nodeid.split("::", 1)[0].replace("\\", "/")
    historical = nodeid in GROUPS["historical_reference_tests"]
    frozen = nodeid in GROUPS["frozen_integrity_tests"]
    external = file in GROUPS["external_modules"]
    financial = historical or frozen or file in GROUPS["financial_modules"]
    if external:
        category = "external_integration"
        reason = GROUPS["external_modules"][file]
        dependencies = ["external Firebase service", "external identity/configuration"]
    elif historical:
        category = "historical_certification"
        reason = "Original unversioned reference required; remains executed in financial/full jobs."
        if "product_api" in file:
            dependencies = [
                "docs/appendices/magic_formula_v12_2/ranking_snapshot.json",
                "data/magic_formula/universe_snapshots.db (ID/digest sector provenance)",
            ]
        elif "canonical_ranking" in file:
            dependencies = [
                "docs/appendices/magic_formula_v9_2/methodological_universe.csv",
                "data/magic_formula/universe_snapshots.db",
                "data/cvm/dfp_cia_aberta_2025.zip",
            ]
        elif "methodology_policy" in file:
            dependencies = [
                "docs/appendices/magic_formula_policy_review_resolution_v8/"
                "methodological_universe_v8.csv"
            ]
        else:
            dependencies = ["data/magic_formula/universe_snapshots.db (historical IDs/order)"]
    elif frozen:
        category = "historical_certification"
        reason = "Self-contained frozen-byte integrity belongs to financial certification."
        dependencies = ["versioned frozen manifest and exact bytes"]
    else:
        category = (
            "unit" if file.startswith(("tests/unit/", "tests/domain/")) else "hermetic_integration"
        )
        reason = None
        dependencies = ["versioned code/fixtures", "temporary SQLite if used", "network denied"]
    return {
        "nodeid": nodeid,
        "file": file,
        "category": category,
        "hermetic_capable": not (historical or external),
        "engineering": not (historical or frozen or external),
        "financial": financial,
        "exclusion_reason": reason,
        "dependencies": dependencies,
        "security_critical": any(x in file for x in ("security", "auth", "upload", "ci/")),
        "financial_critical": financial
        or any(
            x in file
            for x in ("performance", "portfolio", "shares", "magic_formula", "contribution")
        ),
    }


# Prevent pytest from treating the policy helper as a test when imported.
test_scope.__test__ = False


def normalized_message(message: str, root: Path = ROOT) -> str:
    text = message.replace(str(root), "<checkout>").replace(root.as_posix(), "<checkout>")
    text = re.sub(r"[A-Za-z]:[\\/][^\s\"']+", "<absolute-path>", text)
    return " ".join(text.split())


def diagnostic_key(item: dict) -> str:
    return json.dumps(
        {key: item.get(key) for key in ("tool", "file", "line", "column", "code", "message")},
        sort_keys=True,
        ensure_ascii=False,
    )


def compare_diagnostics(actual: list[dict], expected: list[dict]) -> dict:
    observed = Counter(diagnostic_key(item) for item in actual)
    baseline = Counter(diagnostic_key(item) for item in expected)
    added = list((observed - baseline).elements())
    removed = list((baseline - observed).elements())
    return {
        "status": "FAIL" if added else "PASS",
        "policy": "NO_NEW_DIAGNOSTIC_IDENTITIES_OR_MULTIPLICITY",
        "baseline_debt": len(expected),
        "current_debt": len(actual),
        "added": [json.loads(item) for item in added],
        "removed": [json.loads(item) for item in removed],
    }


def summarize_reports(reports: dict[str, dict]) -> dict:
    required = ("runtime", "engineering", "node", "quality")
    missing = [name for name in required if name not in reports]
    identities = {
        (report.get("checkout_sha"), report.get("source_fingerprint"))
        for report in reports.values()
    }
    valid_identity = len(identities) == 1 and all(all(pair) for pair in identities)
    engineering = (
        not missing
        and valid_identity
        and all(reports[name].get("exit_code") == 0 for name in required)
    )
    certification = reports.get("financial", {})
    financial_pass = (
        certification.get("status") == "PASS"
        and certification.get("exit_code") == 0
        and (certification.get("checkout_sha"), certification.get("source_fingerprint"))
        in identities
    )
    return {
        "engineering_ci": "PASS" if engineering else "FAIL",
        "engineering_missing_reports": missing,
        "consistent_identity": valid_identity,
        "financial_certification": "PASS" if financial_pass else "BLOCKED",
        "financial_reasons": certification.get("blockers", ["NO_CERTIFICATION_REPORT"]),
        "release_readiness": "BLOCKED",
        "release_reasons": [
            "Reproducible release artifact/homologation/backup/rollback evidence not implemented",
            "Financial certification requires independent closure",
        ],
        "deployment_authorization": "NOT_IMPLEMENTED",
        "deployment_authorized": False,
        "external_integrations": "NOT_RUN_OFFLINE; see full-suite external cases",
    }
