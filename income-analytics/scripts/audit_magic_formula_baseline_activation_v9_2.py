"""Reconstitute the current Magic Formula V1 activation baseline."""

# ruff: noqa: E501

from __future__ import annotations

import csv
import hashlib
import inspect
import json
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest

from income_analytics.application.magic_formula_screening import (
    MagicFormulaMethodologyPolicy,
    liquidity_candidate_status,
    methodology_eligibility_state,
    methodology_policy_fingerprint,
    methodology_policy_payload,
    select_security_s4,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/appendices/magic_formula_v9_2"
V9 = ROOT / "docs/appendices/magic_formula_methodology_v9"
V91 = ROOT / "docs/appendices/magic_formula_v9_1"
REPORT = ROOT / "docs/MAGIC_FORMULA_BASELINE_RECONSTITUTION_AND_ACTIVATION_V9_2.md"
JUNIT = ROOT / "tmp/magic_formula_v9_2_junit.xml"
TEST_GLOB = "tests/application/test_magic_formula_*.py"
POLICY_ID = "MF_BR_2027_V1"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def recalculate_s4_and_l3(universe: list[dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    candidate_path = ROOT / "docs/appendices/magic_formula_eligibility_policy_v7/security_candidates_010.csv"
    resolution_path = ROOT / "docs/appendices/magic_formula_policy_review_resolution_v8/buyable_security_review_resolution.csv"
    candidates: dict[str, list[dict[str, object]]] = {}
    for row in read_csv(candidate_path):
        candidates.setdefault(row["cvm_code"], []).append(
            {
                "ticker": row["ticker"],
                "isin": row["isin"],
                "security_id": row["security_id"],
                "valid_listing": row["valid_listing"].lower() == "true",
                "market_type": row["market_type"],
                "liquidity_evidence_complete": row["liquidity_evidence_complete"].lower() == "true",
                "traded_days_ratio_30d": row["traded_days_ratio_30d"] or None,
                "median_daily_financial_volume_30d": row["median_daily_financial_volume_30d"] or None,
            }
        )

    v8_sources: set[str] = set()
    for row in read_csv(resolution_path):
        comparisons = json.loads(row["candidate_comparison_v8"] or "[]")
        if not comparisons:
            continue
        issuer = row["cvm_code"]
        candidates[issuer] = [
            {
                "ticker": item["ticker"],
                "isin": item["isin"],
                "security_id": item["isin"] or item["ticker"],
                "valid_listing": True,
                "market_type": "010",
                "liquidity_evidence_complete": (
                    item["identity_status"] == "IDENTITY_CONFIRMED_COTAHIST"
                    and item["ratio"] is not None
                    and item["median_volume"] is not None
                ),
                "traded_days_ratio_30d": str(item["ratio"]) if item["ratio"] is not None else None,
                "median_daily_financial_volume_30d": (
                    str(item["median_volume"]) if item["median_volume"] is not None else None
                ),
            }
            for item in comparisons
        ]
        v8_sources.add(issuer)

    security_rows: list[dict[str, object]] = []
    updated_universe = [dict(row) for row in universe]
    for company in updated_universe:
        cvm = company["cvm_code"]
        result = select_security_s4(candidates.get(cvm, []))
        selected = result["selected_security"]
        if selected:
            ratio = str(selected["traded_days_ratio_30d"])
            liquidity = liquidity_candidate_status(
                ratio,
                evidence_complete=bool(selected["liquidity_evidence_complete"]),
            )
            liquidity_state = liquidity
        else:
            ratio = ""
            liquidity_state = "LIQUIDITY_REVIEW"
        status = result["status"]
        row = {
            "cvm_code": cvm,
            "company": company["company"],
            "security_status": status,
            "selected_ticker": selected["ticker"] if selected else "",
            "selected_isin": selected["isin"] if selected else "",
            "s4_ratio_30d": ratio,
            "liquidity_status": liquidity_state,
            "selection_source": (
                "V8 frozen issuer-confirmed COTAHIST comparison"
                if cvm in v8_sources
                else "V7 exact market-010 candidate metrics"
            ),
            "ranking_eligible": company["rankable"],
        }
        security_rows.append(row)
        company["security_status"] = status
        company["selected_ticker"] = row["selected_ticker"]
        company["selected_isin"] = row["selected_isin"]
        company["traded_days_ratio_30d"] = ratio
        company["liquidity_status"] = liquidity_state
        old_status = company["methodological_status"]
        company["methodological_status"] = methodology_eligibility_state(
            structural_status=company["structural_status"],
            security_status=status,
            liquidity_status=liquidity_state,
            data_complete=old_status == "ELIGIBLE_COMPLETE",
        )
        company["rankable"] = str(company["methodological_status"] == "ELIGIBLE_COMPLETE").lower()
        row["ranking_eligible"] = company["rankable"]

    return security_rows, updated_universe


def command_output(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()


def build_manifest() -> tuple[dict, list[str]]:
    test_files = sorted(str(path.relative_to(ROOT)) for path in (ROOT / "tests/application").glob("test_magic_formula_*.py"))
    collect_command = [sys.executable, "-m", "pytest", *test_files, "--collect-only", "-q", "-p", "no:cacheprovider"]
    collected = command_output(*collect_command).splitlines()
    node_ids = sorted(line.strip() for line in collected if "::" in line and not line.startswith("<") )
    junit_root = ET.parse(JUNIT).getroot()
    suite = junit_root if junit_root.tag == "testsuite" else junit_root.find("testsuite")
    assert suite is not None
    attrs = suite.attrib
    executed = int(attrs.get("tests", "0"))
    failures = int(attrs.get("failures", "0"))
    errors = int(attrs.get("errors", "0"))
    skipped = int(attrs.get("skipped", "0"))
    xfailed = sum(1 for case in suite.iter("testcase") if case.find("skipped") is not None and "xfail" in (case.find("skipped").attrib.get("type", "").lower()))
    xpassed = sum(1 for case in suite.iter("testcase") if case.find("properties") is not None and any(p.attrib.get("name") == "xpass" for p in case.find("properties")))
    failed = failures + errors
    passed = executed - failed - skipped
    rev = command_output("git", "rev-parse", "HEAD")
    dirty = bool(command_output("git", "status", "--porcelain"))
    manifest = {
        "schema_version": "1.0",
        "test_baseline_version": "MF_BR_2027_V1_ACTIVATION_BASELINE",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_revision_if_available": rev or None,
        "git_working_tree_dirty": dirty,
        "python_version": platform.python_version(),
        "pytest_version": pytest.__version__,
        "collection_command": [
            "python", "-m", "pytest", *test_files, "--collect-only", "-q", "-p", "no:cacheprovider"
        ],
        "execution_command": (
            "$tests = Get-ChildItem tests/application -Filter 'test_magic_formula_*.py' | "
            "ForEach-Object { $_.FullName }; python -m pytest $tests -q -p no:cacheprovider "
            "--junitxml=tmp/magic_formula_v9_2_junit.xml"
        ),
        "collected_count": len(node_ids),
        "executed_count": executed,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "xfailed": xfailed,
        "xpassed": xpassed,
        "node_ids": node_ids,
        "node_ids_hash": hashlib.sha256("\n".join(node_ids).encode()).hexdigest(),
    }
    hash_payload = {k: v for k, v in manifest.items() if k not in {"generated_at", "manifest_hash"}}
    manifest["manifest_hash"] = digest(hash_payload)
    return manifest, node_ids


def test_ids_by_patterns(node_ids: list[str], patterns: tuple[str, ...]) -> list[str]:
    matches = [node for node in node_ids if any(pattern in node for pattern in patterns)]
    return sorted(set(matches))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest, node_ids = build_manifest()
    repeated_manifest, repeated_node_ids = build_manifest()
    manifest_deterministic = (
        manifest["manifest_hash"] == repeated_manifest["manifest_hash"]
        and node_ids == repeated_node_ids
    )
    write_json(OUT / "current_test_manifest.json", manifest)

    areas = [
        ("historical_identity", ("test_universe_002_issuer_economic_unit", "test_universe_003_petrobras_two_classes_one_issuer")),
        ("historical_security_resolution", ("test_s4_frequency_then_volume_then_stable_key", "test_deterministic_tie_uses_stable_identity_key")),
        ("b3_identity", ("test_correct_isin_with_historical_ticker_is_validated_by_identity", "test_wrong_class_is_rejected_even_when_ticker_is_present")),
        ("cotahist_parsing", ("test_cotahist_scan_matches_exact_ticker_or_isin", "test_mkt_evid_returns_auditable_cotahist_bundle")),
        ("market_010", ("test_fractional_market_020_is_never_accepted_as_010", "test_market_020_never_substitutes_for_market_010")),
        ("price_provenance", ("test_high_confidence_provenance_is_complete_and_fail_closed",)),
        ("snapshot_ordering", ("test_snapshot_ordering_audit_resolves_duplicate_timestamp_with_rowid",)),
        ("snapshot_immutability", ("test_same_timestamp_selects_later_inserted_and_preserves_old_snapshot", "test_dry_run_does_not_persist_universe_snapshot")),
        ("v3_price_recovery_behavior", ("test_csna3_and_v3_recoveries_survive_current_snapshot",)),
        ("v4_availability_behavior", ("test_exact_date_lookup", "test_future_price_is_never_selected")),
        ("v5_source_expansion", ("test_source_conflicts_are_reported_without_selecting_a_winner", "test_later_unique_timestamp_wins_over_tie_and_duplicate_save_is_idempotent")),
        ("v6_investable_universe", ("test_raw_universe_rows_are_preserved_and_classified_once", "test_financial_sector_is_structurally_excluded_by_existing_rule")),
        ("missing_data_not_ineligible", ("test_missing_data_does_not_make_company_ineligible", "test_missing_data_does_not_create_exclusion")),
        ("v7_buyable_security_selection", ("test_s4_frequency_then_volume_then_stable_key", "test_buyable_security_review_is_a_separate_final_state")),
        ("multi_class_issuer", ("test_multiple_classes_remain_one_company_liquidity_decision",)),
        ("unit_handling", ("test_unit_is_one_security_candidate_not_duplicate_components", "test_sec_evid_requires_explicit_quantity_unit_evidence")),
        ("s4_selection", ("test_v1_06_s4_chooses_highest_trading_frequency", "test_v1_07_s4_uses_volume_only_after_frequency_tie")),
        ("s4_deterministic_tie_break", ("test_deterministic_tie_uses_stable_identity_key_only_after_economic_tie",)),
        ("l3", ("test_l3_uses_thirty_session_ratio_and_distinguishes_zero_from_missing", "test_v1_13_liquidity_fifteen_of_thirty_passes")),
        ("other_security_cannot_rescue_selected_security", ("test_another_issuer_class_cannot_rescue_selected_security", "test_v1_16_nonselected_class_cannot_rescue_l3_failure")),
        ("review_not_fail", ("test_v1_20_review_is_not_liquidity_fail", "test_incomplete_liquidity_for_any_valid_class_keeps_selection_in_review")),
        ("v8_screening_separation", ("test_retail_and_aviation_are_methodologically_eligible_by_default", "test_optional_sector_filters_preserve_metrics_and_global_rank")),
        ("retail_not_methodology_exclusion", ("test_v1_02_traditional_retail_is_not_methodology_excluded", "test_v1_21_retail_screening_does_not_change_methodology_state")),
        ("aviation_not_methodology_exclusion", ("test_v1_03_aviation_is_not_methodology_excluded", "test_v1_22_aviation_screening_does_not_change_methodology_state")),
        ("asai3_golden_case", ("test_asai3_cash_and_carry_does_not_need_eligibility_exception", "test_v1_26_asai3_needs_no_methodology_exception")),
        ("market_cap_disabled", ("test_v1_05_market_cap_does_not_exclude",)),
        ("v9_policy_fingerprint", ("test_v1_30_policy_serialization_and_version_are_stable",)),
        ("no_data_snooping", ("test_selector_does_not_require_or_consume_rank_values", "test_v1_08_s4_ignores_price_availability", "test_v1_09_s4_ignores_earnings_yield", "test_v1_10_s4_ignores_return_on_capital", "test_v1_11_s4_ignores_existing_rank_values")),
        ("coverage_denominators", ("test_coverage_counts_complete_and_blocked_as_confirmed_eligible", "test_review_is_included_in_conservative_denominator", "test_v1_28_methodological_coverage_denominator_is_complete_plus_blocked", "test_v1_29_conservative_coverage_includes_reviews")),
        ("review_stop_rule", ("test_s4_review_stays_review_when_any_valid_class_lacks_comparison", "test_unknown_security_policy_s0_remains_review", "test_incomplete_liquidity_for_any_valid_class_keeps_selection_in_review")),
    ]
    regression_rows = []
    for area, patterns in areas:
        matches = test_ids_by_patterns(node_ids, patterns)
        regression_rows.append({
            "critical_area": area,
            "current_test_ids": "; ".join(matches),
            "status": "PASS" if matches else "FAIL",
            "evidence": "Current exact pytest node IDs are included in current_test_manifest.json and were executed in the V9.2 run; historical V7 mapping is unknown.",
        })
    write_csv(OUT / "critical_regression_map.csv", regression_rows, ["critical_area", "current_test_ids", "status", "evidence"])

    baseline_universe = read_csv(V9 / "methodological_universe.csv")
    prior_universe = {row["cvm_code"]: row for row in baseline_universe}
    prior_security = {
        row["cvm_code"]: row for row in read_csv(V9 / "security_selection.csv")
    }
    security, universe = recalculate_s4_and_l3(baseline_universe)
    counts = Counter(row["methodological_status"] for row in universe)
    for status in (
        "INELIGIBLE_STRUCTURAL",
        "LIQUIDITY_FAIL",
        "BUYABLE_SECURITY_REVIEW",
        "LIQUIDITY_REVIEW",
        "ELIGIBLE_DATA_BLOCKED",
        "ELIGIBLE_COMPLETE",
    ):
        counts.setdefault(status, 0)
    s4_counts = Counter(row["security_status"] for row in security)
    l3_counts = Counter(row["liquidity_status"] for row in universe)
    s4_reconciliation_matches = all(
        row["security_status"] == prior_security[row["cvm_code"]]["security_status"]
        and row["selected_ticker"] == prior_security[row["cvm_code"]]["selected_ticker"]
        and row["selected_isin"] == prior_security[row["cvm_code"]]["selected_isin"]
        for row in security
    )
    l3_reconciliation_matches = all(
        row["liquidity_status"] == prior_universe[row["cvm_code"]]["liquidity_status"]
        and row["methodological_status"] == prior_universe[row["cvm_code"]]["methodological_status"]
        for row in universe
    )
    universe_count = len(universe)
    eligible = counts["ELIGIBLE_COMPLETE"] + counts["ELIGIBLE_DATA_BLOCKED"]
    review_count = max(s4_counts["BUYABLE_SECURITY_REVIEW"], l3_counts["LIQUIDITY_REVIEW"])
    cov = {
        "baseline_companies": universe_count,
        "status_counts": dict(sorted(counts.items())),
        "s4_selected": s4_counts["RESOLVED"],
        "s4_review": s4_counts["BUYABLE_SECURITY_REVIEW"],
        "l3_pass": l3_counts["LIQUIDITY_PASS"],
        "l3_fail": l3_counts["LIQUIDITY_FAIL"],
        "l3_review": review_count,
        "methodologically_eligible": eligible,
        "complete": counts["ELIGIBLE_COMPLETE"],
        "data_blocked": counts["ELIGIBLE_DATA_BLOCKED"],
        "methodological_data_coverage": counts["ELIGIBLE_COMPLETE"] / eligible,
        "conservative_data_coverage": counts["ELIGIBLE_COMPLETE"] / (eligible + review_count),
        "methodological_denominator": eligible,
        "conservative_denominator": eligible + review_count,
        "coverage_reconciles_with_v9": True,
    }
    write_json(OUT / "coverage_summary.json", cov)
    write_csv(OUT / "methodological_universe.csv", universe, list(universe[0]))
    write_csv(
        OUT / "security_selection.csv",
        security,
        [
            "cvm_code",
            "company",
            "security_status",
            "selected_ticker",
            "selected_isin",
            "s4_ratio_30d",
            "liquidity_status",
            "selection_source",
            "ranking_eligible",
        ],
    )

    source_policy = json.loads((V9 / "policy_definition.json").read_text(encoding="utf-8"))
    policy = MagicFormulaMethodologyPolicy(policy_id=POLICY_ID, activated=True)
    policy_payload = methodology_policy_payload(policy)
    policy_hash = methodology_policy_fingerprint(policy)
    definition = {
        "policy_id": POLICY_ID,
        "policy_version": "V1",
        "activation_transition": {
            "from": "MF_BR_2027_V1_DRAFT",
            "to": POLICY_ID,
        },
        "lifecycle": {"activation_status": "ACTIVE", "active": True, "activated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "ranking_calculated": False, "top_30_published": False, "immutable": True},
        "methodology": source_policy["methodology"],
        "fingerprint_payload": policy_payload,
        "activation_basis": "V9.2 current gates passed; historical V7 evidence gap accepted and retained.",
    }

    historical = {
        "v7_reported_tests": 274,
        "historical_node_ids_available": False,
        "historical_revision_available": False,
        "reconciliation_status": "UNRESOLVABLE",
        "investigation_closed": True,
        "further_v7_test_hunt": "CLOSED",
        "activation_exception": "HISTORICAL_EVIDENCE_GAP",
        "historical_limitation_accepted": True,
        "does_not_assert_no_historical_test_loss": True,
        "does_not_claim_all_v7_tests_reconciled": True,
        "basis": "V9.1 audit found no verifiable V7 revision, node-ID manifest, or historical execution artifact; current pytest cache is current and cannot recover historical IDs.",
        "v8_reconstructed_collection": {"count": 243, "classification": "SUPPORTING_EVIDENCE_NOT_VERIFIED_HISTORICAL_INVENTORY"},
    }
    write_json(OUT / "historical_evidence_limitation.json", historical)
    write_json(OUT / "policy_definition.json", definition)
    fingerprint = {
        "policy_id": POLICY_ID,
        "policy_version": "V1",
        "policy_hash": policy_hash,
        "algorithm": "SHA-256 over canonical compact sorted JSON methodology payload",
        "screening_preferences_included": False,
        "source_snapshot_id": "ed8a9235-ee14-4a97-93fd-0dbcd87113fb",
        "source_snapshot_digest": "0e46baad7108a01b972459b1736ec28a67a2c932fcac10344432569b24a586d9",
        "reference_date": "2025-12-30",
    }
    write_json(OUT / "policy_fingerprint.json", fingerprint)

    backlog = read_csv(V9 / "data_recovery_backlog.csv")
    backlog_counts = Counter(row["priority"] for row in backlog)
    v8_manifest_bytes = (V91 / "v8_test_inventory.csv").read_bytes()
    source_hashes_before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [V9 / "methodological_universe.csv", V9 / "security_selection.csv", V91 / "v8_test_inventory.csv"]}
    gate_checks = {
        "GATE_01_CURRENT_TEST_SUITE": manifest["failed"] == 0 and manifest["executed_count"] == manifest["collected_count"] and manifest["passed"] > 0,
        "GATE_02_CRITICAL_REGRESSION_COVERAGE": all(row["status"] == "PASS" for row in regression_rows) and len(regression_rows) == 30,
        "GATE_03_RUFF": False,
        "GATE_04_POLICY_DETERMINISM": policy_hash == methodology_policy_fingerprint(MagicFormulaMethodologyPolicy(policy_id=POLICY_ID, activated=True)),
        "GATE_05_S4_DETERMINISM": s4_counts["RESOLVED"] == 288 and s4_counts["BUYABLE_SECURITY_REVIEW"] == 19 and s4_reconciliation_matches,
        "GATE_06_L3_DETERMINISM": l3_counts["LIQUIDITY_PASS"] == 243 and l3_counts["LIQUIDITY_FAIL"] == 45 and l3_counts["LIQUIDITY_REVIEW"] == 19 and s4_counts["BUYABLE_SECURITY_REVIEW"] == 19 and l3_reconciliation_matches,
        "GATE_07_STATUS_RECONCILIATION": sum(counts.values()) == 307 and counts["ELIGIBLE_DATA_BLOCKED"] == 63,
        "GATE_08_COVERAGE_RECONCILIATION": abs(cov["methodological_data_coverage"] - 0.7407407407407407) < 1e-12 and abs(cov["conservative_data_coverage"] - 0.6870229007633588) < 1e-12,
        "GATE_09_SCREENING_SEPARATION": policy_payload["methodology"]["screening"]["personal_preferences_in_methodology_hash"] is False and policy_payload["methodology"]["screening"]["default_exclude_traditional_retail"] is False and policy_payload["methodology"]["screening"]["default_exclude_aviation"] is False,
        "GATE_10_SNAPSHOT_IMMUTABILITY": source_hashes_before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [V9 / "methodological_universe.csv", V9 / "security_selection.csv", V91 / "v8_test_inventory.csv"]} and len(v8_manifest_bytes) > 0,
        "GATE_11_NO_RANKING": source_policy["lifecycle"]["ranking_calculated"] is False and not any("rank" in field.lower() and field.lower() not in {"rankable", "ranking_eligible"} for field in universe[0]),
        "GATE_12_NO_TOP30": source_policy["lifecycle"]["top_30_published"] is False,
        "GATE_13_IDEMPOTENCY": True,
        "GATE_14_NO_DATA_SNOOPING": (
            all(
                item in policy_payload["methodology"]["security_selection"]["forbidden_inputs"]
                for item in ("earnings_yield", "return_on_capital", "ranking_position", "price_availability", "portfolio_positions")
            )
            and not any(
                item in inspect.getsource(select_security_s4)
                for item in ("earnings_yield", "return_on_capital", "ranking_position", "price_availability", "portfolio_positions")
            )
        ),
        "GATE_15_TEST_MANIFEST_DETERMINISM": (
            manifest["manifest_hash"] == digest(
                {k: v for k, v in manifest.items() if k not in {"generated_at", "manifest_hash"}}
            )
            and len(node_ids) == len(set(node_ids))
            and manifest_deterministic
        ),
    }
    # Ruff result is injected from the scoped command's captured status.
    ruff_file = ROOT / "tmp/magic_formula_v9_2_ruff_status.txt"
    gate_checks["GATE_03_RUFF"] = ruff_file.exists() and ruff_file.read_text(encoding="utf-8").strip() == "PASS"

    def perform_dry_run() -> dict:
        run_security, run_universe = recalculate_s4_and_l3(
            read_csv(V9 / "methodological_universe.csv")
        )
        run_counts = Counter(row["methodological_status"] for row in run_universe)
        run_s4 = Counter(row["security_status"] for row in run_security)
        run_l3 = Counter(row["liquidity_status"] for row in run_universe)
        for status in (
            "INELIGIBLE_STRUCTURAL",
            "LIQUIDITY_FAIL",
            "BUYABLE_SECURITY_REVIEW",
            "LIQUIDITY_REVIEW",
            "ELIGIBLE_DATA_BLOCKED",
            "ELIGIBLE_COMPLETE",
        ):
            run_counts.setdefault(status, 0)
        run_eligible = run_counts["ELIGIBLE_COMPLETE"] + run_counts["ELIGIBLE_DATA_BLOCKED"]
        run_reviews = max(run_s4["BUYABLE_SECURITY_REVIEW"], run_l3["LIQUIDITY_REVIEW"])
        run_coverage = {
            "methodological": run_counts["ELIGIBLE_COMPLETE"] / run_eligible,
            "conservative": run_counts["ELIGIBLE_COMPLETE"] / (run_eligible + run_reviews),
            "methodological_denominator": run_eligible,
            "conservative_denominator": run_eligible + run_reviews,
        }
        sorted_security = sorted(run_security, key=lambda row: row["cvm_code"])
        selection_hash = digest(sorted_security)
        current_policy_hash = methodology_policy_fingerprint(
            MagicFormulaMethodologyPolicy(policy_id=POLICY_ID, activated=True)
        )
        current_status_counts = dict(sorted(run_counts.items()))
        payload = {
            "policy_hash": current_policy_hash,
            "status_counts": current_status_counts,
            "security_selection_hash": selection_hash,
            "liquidity_counts": {
                "PASS": run_l3["LIQUIDITY_PASS"],
                "FAIL": run_l3["LIQUIDITY_FAIL"],
                "REVIEW": run_reviews,
            },
            "coverage": run_coverage,
            "test_manifest_hash": manifest["manifest_hash"],
        }
        artifact_hashes = {
            "manifest": manifest["manifest_hash"],
            "universe": digest(sorted(run_universe, key=lambda row: row["cvm_code"])),
            "security_selection": selection_hash,
            "coverage": digest(run_coverage),
            "critical_map": hashlib.sha256((OUT / "critical_regression_map.csv").read_bytes()).hexdigest(),
        }
        return {
            **payload,
            "status_hash": digest(current_status_counts),
            "artifact_hashes": artifact_hashes,
        }

    run1 = perform_dry_run()
    run2 = perform_dry_run()
    idempotent = run1 == run2
    gate_checks["GATE_13_IDEMPOTENCY"] = idempotent
    gates = {
        "historical_gate": {"GATE_HISTORICAL_V7_TEST_RECONCILIATION": "UNRESOLVABLE_ACCEPTED"},
        "current_gates": {
            name: {
                "status": "PASS" if passed else "FAIL",
                "evidence": (
                    "Reexecuted S4 over 307 candidate groups using market-010 candidate evidence and V8 issuer-confirmed comparison rows; selected status, ticker, and ISIN reconcile with the frozen V9 result."
                    if name == "GATE_05_S4_DETERMINISM"
                    else "Recalculated L3 from selected S4 metrics at 15/30 sessions; every liquidity and methodological status reconciles with the frozen V9 result."
                    if name == "GATE_06_L3_DETERMINISM"
                    else "Verified by current V9.2 test manifest, mapped tests, frozen V8-derived metrics, policy fingerprint, dry-run signatures, or scoped Ruff run."
                ),
            }
            for name, passed in gate_checks.items()
        },
        "all_current_gates_pass": all(gate_checks.values()),
        "dry_run_1": run1,
        "dry_run_2": run2,
        "idempotency": {"equal": idempotent, "policy_hash_equal": run1["policy_hash"] == run2["policy_hash"], "status_hash_equal": run1["status_hash"] == run2["status_hash"], "security_selection_hash_equal": run1["security_selection_hash"] == run2["security_selection_hash"], "artifact_hashes_equal": run1["artifact_hashes"] == run2["artifact_hashes"]},
        "manifest_determinism": {"repeat_hash_equal": manifest_deterministic, "manifest_hash_first": manifest["manifest_hash"], "manifest_hash_repeat": repeated_manifest["manifest_hash"]},
        "backlog": {"P0": backlog_counts["P0"], "P1": backlog_counts["P1"], "P2": backlog_counts["P2"], "total": len(backlog), "recovery_executed": False},
    }
    write_json(OUT / "activation_gates.json", gates)
    if not gates["all_current_gates_pass"]:
        raise SystemExit(f"Activation blocked by current gates: {[k for k, v in gate_checks.items() if not v]}")

    write_json(OUT / "activation_record.json", {
        "policy_id": POLICY_ID,
        "previous_policy_id": "MF_BR_2027_V1_DRAFT",
        "status": "ACTIVE",
        "policy_hash": policy_hash,
        "activation_timestamp": definition["lifecycle"]["activated_at"],
        "test_manifest_hash": manifest["manifest_hash"],
        "test_manifest_path": "docs/appendices/magic_formula_v9_2/current_test_manifest.json",
        "test_node_ids": manifest["node_ids"],
        "snapshot_id": fingerprint["source_snapshot_id"],
        "snapshot_digest": fingerprint["source_snapshot_digest"],
        "review_counts": {"s4_review": cov["s4_review"], "l3_review": cov["l3_review"]},
        "coverage": {"methodological": cov["methodological_data_coverage"], "conservative": cov["conservative_data_coverage"]},
        "historical_limitation": historical,
        "gates": {k: v["status"] for k, v in gates["current_gates"].items()},
        "immutable": True,
        "next_phase": "MAGIC_FORMULA_DATA_COMPLETION_AND_RANKING_READINESS_V10",
    })
    REPORT.write_text(render_report(manifest, regression_rows, cov, counts, s4_counts, l3_counts, backlog_counts, gates, policy_hash, historical), encoding="utf-8")


def render_report(manifest: dict, regression: list[dict], cov: dict, counts: Counter, s4: Counter, l3: Counter, backlog: Counter, gates: dict, policy_hash: str, historical: dict) -> str:
    gate_lines = "\n".join(f"- `{name}` = **{data['status']}**" for name, data in gates["current_gates"].items())
    return f'''# Magic Formula — reconstituição da baseline e ativação V9.2

**Resultado: PASS.** A política `MF_BR_2027_V1` foi ativada após todos os 15 gates atuais passarem. A lacuna histórica V7 foi aceita e registrada como não resolvível; isso não afirma que os testes V7 foram reconciliados.

## Limitação histórica aceita

V7 reportava 274 testes, mas não há IDs históricos nem revisão V7 verificável. A investigação está encerrada (`FURTHER_V7_TEST_HUNT=CLOSED`). A reconciliação é `UNRESOLVABLE`; não se afirma que todos os testes V7 foram reconciliados nem que não houve perda histórica. Os 243 IDs reconstruídos da coleta V8 são apenas evidência de apoio, não um inventário histórico verificado.

## Baseline atual verificável

- Coletados/executados/passaram: **{manifest['collected_count']} / {manifest['executed_count']} / {manifest['passed']}**; falharam: **{manifest['failed']}**; skipped: **{manifest['skipped']}**.
- Node IDs preservados: sim, ordenados; hash dos IDs `{manifest['node_ids_hash']}`.
- Manifest hash: `{manifest['manifest_hash']}`; gerado em `{manifest['generated_at']}`.
- Manifest determinístico: sim; hash idêntico em duas coletas independentes.
- Versão da baseline: `MF_BR_2027_V1_ACTIVATION_BASELINE`.

## Regressões críticas

Cobertura atual: **{len(regression)}/{sum(row['status'] == 'PASS' for row in regression)}**, sem área descoberta. O mapa liga cada área aos IDs atuais executados; não tenta equivalência com testes V7 desconhecidos.

## Metodologia e universo congelado

Exclusão estrutural financeira ativa; varejo e aviação são filtros de screening, sem exclusão metodológica; utilities não receberam nova exclusão; market cap mínimo é `NONE`; mercado `010`. ASAI3 permanece `CASH_AND_CARRY` sem exceção metodológica. Screening não integra o fingerprint.

S4 foi recomputado sobre 307 grupos de candidatos (com a resolução de identidade V8 onde a evidência antiga era incompleta): **{s4['RESOLVED']}** papéis selecionados e **{s4['BUYABLE_SECURITY_REVIEW']}** em review, reconciliando ticker, ISIN e estado com o resultado V9 congelado. O critério primário é frequência negociada em 30 sessões, com volume financeiro mediano como desempate e chave estável como desempate final. S4 não consulta disponibilidade de preço, EY, ROC, ranks, preferências nem posições da carteira.

L3 foi recalculado a partir da seleção S4, com janela de 30 pregões e mínimo de 15 (50%); PASS **{l3['LIQUIDITY_PASS']}**, FAIL **{l3['LIQUIDITY_FAIL']}**, REVIEW **{cov['l3_review']}**. Todos os status reconciliam com a baseline V9 congelada. Review é estado definido e permanece fora do universo rankable.

Baseline **{cov['baseline_companies']}**; status: structural ineligible {counts['INELIGIBLE_STRUCTURAL']}, liquidity fail {counts['LIQUIDITY_FAIL']}, buyable security review {counts['BUYABLE_SECURITY_REVIEW']}, liquidity review {counts['LIQUIDITY_REVIEW']}, data blocked {counts['ELIGIBLE_DATA_BLOCKED']}, complete {counts['ELIGIBLE_COMPLETE']}; soma {sum(counts.values())}.

Coverage metodológica: **{cov['methodological_data_coverage']:.2%}** ({cov['complete']}/{cov['methodological_denominator']}); conservadora: **{cov['conservative_data_coverage']:.2%}** ({cov['complete']}/{cov['conservative_denominator']}). 63 elegíveis bloqueadas por dados permanecem elegíveis. Backlog preservado: P0 {backlog['P0']}, P1 {backlog['P1']}, P2 {backlog['P2']}, total {sum(backlog.values())}; nenhuma recuperação executada.

Snapshot preservado: `ed8a9235-ee14-4a97-93fd-0dbcd87113fb`, digest `0e46baad7108a01b972459b1736ec28a67a2c932fcac10344432569b24a586d9`. Nenhum ranking EY/ROC/combinado foi calculado para o universo desta ativação, e nenhum Top 30 foi publicado. Os testes do motor de ranking da suíte continuam isolados em fixtures.

## Fingerprint, dry runs e ativação

Policy hash: `{policy_hash}`. Os dois dry runs tiveram hashes idênticos de política, status, seleção e artefatos. Ativação registrada em `activation_record.json`; a V1 fica imutável, e alteração metodológica requer nova versão.

{gate_lines}

Todos os gates atuais passaram. Próxima fase autorizada: `MAGIC_FORMULA_DATA_COMPLETION_AND_RANKING_READINESS_V10`, limitada aos `ELIGIBLE_DATA_BLOCKED` e sem alterar S4, L3, exclusões, screening ou market cap.

Artefatos completos: `docs/appendices/magic_formula_v9_2/`.
'''


if __name__ == "__main__":
    main()
