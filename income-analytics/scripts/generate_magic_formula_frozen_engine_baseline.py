"""Generate the prospective, deterministic MF_BR_2027_V1 engine baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from income_analytics.application.magic_formula_screening import (
    MagicFormulaMethodologyPolicy,
    methodology_policy_fingerprint,
)

BASELINE_ID = "MF_BR_2027_V1_FROZEN_ENGINE_BASELINE_V2"
CONTRACT_VERSION = "MF_BR_2027_V1_FROZEN_ENGINE_SEMANTICS_V1"
POLICY_HASH = "96d5d54ab1b1320ddc14f1a3c9cd6764b1bf8d68f1e6d79ffd0faa6d1b72cbac"
RANKING_HASH = "f1ee50809c83979ba221d84ebb48150b9470331240940f89a8cb745f2a4ee8f3"
CANONICAL_RESULT_SHA256 = "162c1b2f8856ae7d88cf5809d9418395464d0b2042bf6177fb48141e5b4fcf6a"
GOLDENS_REL = (
    "docs/appendices/multiportfolio_v2_certification_closure/frozen_engine_semantic_goldens.json"
)
CONTRACT_REL = (
    "docs/appendices/multiportfolio_v2_certification_closure/frozen_engine_semantic_contract.md"
)
RECONCILIATION_REL = (
    "docs/appendices/multiportfolio_v2_certification_closure/magic_formula_reconciliation.json"
)
SNAPSHOT_REL = "docs/appendices/magic_formula_v12_2/ranking_snapshot.json"
POLICY_ARTIFACTS = (
    "docs/appendices/magic_formula_v9_2/policy_definition.json",
    "docs/appendices/magic_formula_v9_2/policy_fingerprint.json",
    "docs/appendices/magic_formula_v9_2/activation_record.json",
    "docs/appendices/magic_formula_v9_2/activation_gates.json",
    "docs/appendices/magic_formula_v12_2/release_gate.json",
    SNAPSHOT_REL,
)

# Explicit implementation dependency closure for share/security identity,
# quantity units, market selection, issuer market-cap diagnostics and ranking.
PROTECTED_FILES = (
    "src/income_analytics/application/cvm_magic_formula_normalization.py",
    "src/income_analytics/application/historical_shares_units.py",
    "src/income_analytics/application/issuer_market_cap.py",
    "src/income_analytics/application/magic_formula_canonical_ranking.py",
    "src/income_analytics/application/magic_formula_contract.py",
    "src/income_analytics/application/magic_formula_eligibility_policy_v7.py",
    "src/income_analytics/application/magic_formula_fundamentals_assembler.py",
    "src/income_analytics/application/magic_formula_formal_qa.py",
    "src/income_analytics/application/magic_formula_investable_universe.py",
    "src/income_analytics/application/magic_formula_preview.py",
    "src/income_analytics/application/magic_formula_ranking_validation.py",
    "src/income_analytics/application/magic_formula_screening.py",
    "src/income_analytics/application/magic_formula_security_capital_evidence.py",
    "src/income_analytics/application/magic_formula_stocks.py",
    "src/income_analytics/application/magic_formula_universe.py",
    "src/income_analytics/application/market_data.py",
    "src/income_analytics/application/monetary_amount.py",
    "src/income_analytics/infrastructure/cvm_capital_structure.py",
    "src/income_analytics/infrastructure/cvm_fundamentals_data.py",
    "src/income_analytics/infrastructure/cvm_historical_shares_document.py",
    "src/income_analytics/infrastructure/magic_formula_historical_price_sources.py",
    "src/income_analytics/infrastructure/magic_formula_universe_sources.py",
    "src/income_analytics/infrastructure/magic_formula_universe_repository.py",
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _git_commit(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _pytest_version() -> str:
    try:
        return version("pytest")
    except PackageNotFoundError:
        return "NOT_INSTALLED"


def _test_files(root: Path) -> list[str]:
    relevant = []
    for directory in (root / "tests/application", root / "tests/api"):
        for path in directory.glob("test_*.py"):
            name = path.name
            if name.startswith("test_magic_formula") or name in {
                "test_historical_shares_units.py",
                "test_issuer_market_cap.py",
                "test_cvm_magic_formula_normalization.py",
                "test_petrobras_canonical_e2e.py",
            }:
                relevant.append(path.relative_to(root).as_posix())
    return sorted(relevant)


def _read_json(root: Path, relative: str) -> dict:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _validate_canonical_state(root: Path) -> dict:
    policy = MagicFormulaMethodologyPolicy()
    actual_policy_hash = methodology_policy_fingerprint(policy)
    if actual_policy_hash != POLICY_HASH:
        raise ValueError("MF_POLICY_HASH_DRIFT")

    snapshot = _read_json(root, SNAPSHOT_REL)
    release = _read_json(root, "docs/appendices/magic_formula_v12_2/release_gate.json")
    reconciliation = _read_json(root, RECONCILIATION_REL)
    rows = snapshot.get("results", [])
    if not (
        snapshot.get("policy_id")
        == release.get("policy_id")
        == reconciliation.get("policy_id")
        == "MF_BR_2027_V1"
        and snapshot.get("policy_hash")
        == release.get("policy_hash_after")
        == reconciliation.get("policy_hash")
        == POLICY_HASH
        and snapshot.get("ranking_snapshot_id")
        == release.get("snapshot_id")
        == reconciliation.get("snapshot_id")
        == "mf-f1ee50809c83979ba221d84e"
        and snapshot.get("ranking_hash")
        == release.get("ranking_hash")
        == reconciliation.get("ranking_hash")
        == RANKING_HASH
        and len(rows) == release.get("ranked") == reconciliation.get("ranked_company_count") == 165
        and len({row.get("company_id") for row in rows}) == 165
        and all(
            all(
                key in row
                for key in (
                    "earnings_yield",
                    "return_on_capital",
                    "earnings_yield_rank",
                    "return_on_capital_rank",
                    "global_rank",
                )
            )
            and row["combined_score"] == row["earnings_yield_rank"] + row["return_on_capital_rank"]
            for row in rows
        )
        and reconciliation.get("canonical_result_sha256") == CANONICAL_RESULT_SHA256
    ):
        raise ValueError("CANONICAL_RANKING_RECONCILIATION_FAILED")
    return {
        "policy_id": "MF_BR_2027_V1",
        "policy_hash": POLICY_HASH,
        "active_snapshot_id": snapshot["ranking_snapshot_id"],
        "ranking_hash": RANKING_HASH,
        "ranked_company_count": 165,
        "canonical_result_sha256": CANONICAL_RESULT_SHA256,
        "snapshot_artifact_sha256": _sha256((root / SNAPSHOT_REL).read_bytes()),
    }


def build_payload(root: Path, *, git_commit: str | None = None) -> dict:
    root = root.resolve()
    canonical = _validate_canonical_state(root)
    goldens = _read_json(root, GOLDENS_REL)
    if goldens.get("semantic_contract_version") != CONTRACT_VERSION:
        raise ValueError("SEMANTIC_CONTRACT_VERSION_MISMATCH")
    if not (root / CONTRACT_REL).is_file():
        raise ValueError("SEMANTIC_CONTRACT_MISSING")

    protected_files = [
        {"path": path, "sha256": _sha256((root / path).read_bytes())}
        for path in sorted(PROTECTED_FILES)
    ]
    test_manifest = [
        {"path": path, "sha256": _sha256((root / path).read_bytes())} for path in _test_files(root)
    ]
    golden_tests = [
        {
            "rule_id": golden["rule_id"],
            "test_node_id": (
                "tests/application/test_magic_formula_frozen_engine_semantics.py::"
                f"test_frozen_engine_semantic_golden[{golden['rule_id']}]"
            ),
        }
        for golden in goldens["goldens"]
    ]
    golden_manifest = {
        "golden_file": GOLDENS_REL,
        "golden_file_sha256": _sha256((root / GOLDENS_REL).read_bytes()),
        "test_file": "tests/application/test_magic_formula_frozen_engine_semantics.py",
        "test_file_sha256": _sha256(
            (root / "tests/application/test_magic_formula_frozen_engine_semantics.py").read_bytes()
        ),
        "cases": golden_tests,
    }
    return {
        "schema_version": "1.0",
        "baseline_id": BASELINE_ID,
        "git_commit": git_commit or _git_commit(root),
        "methodology": {
            "policy_id": canonical["policy_id"],
            "policy_hash": canonical["policy_hash"],
            "active_snapshot_id": canonical["active_snapshot_id"],
            "ranking_hash": canonical["ranking_hash"],
            "ranked_company_count": canonical["ranked_company_count"],
            "canonical_result_sha256": canonical["canonical_result_sha256"],
            "snapshot_artifact_sha256": canonical["snapshot_artifact_sha256"],
        },
        "semantic_contract_version": CONTRACT_VERSION,
        "semantic_contract_sha256": _sha256((root / CONTRACT_REL).read_bytes()),
        "generator": {
            "path": "scripts/generate_magic_formula_frozen_engine_baseline.py",
            "sha256": _sha256(
                (root / "scripts/generate_magic_formula_frozen_engine_baseline.py").read_bytes()
            ),
        },
        "protected_files": protected_files,
        "policy_artifacts": [
            {"path": path, "sha256": _sha256((root / path).read_bytes())}
            for path in sorted(POLICY_ARTIFACTS)
        ],
        "golden_test_manifest": golden_manifest,
        "golden_test_manifest_sha256": _sha256(_canonical_json(golden_manifest)),
        "test_manifest": test_manifest,
        "test_manifest_sha256": _sha256(_canonical_json(test_manifest)),
        "runtime": {
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "pytest_version": _pytest_version(),
            "file_hash_algorithm": "SHA-256 raw bytes",
            "payload_hash_encoding": "UTF-8 compact sorted-key JSON",
        },
    }


def build_document(root: Path, *, generated_at: str | None = None) -> dict:
    payload = build_payload(root)
    return {
        "payload": payload,
        "payload_sha256": _sha256(_canonical_json(payload)),
        "creation_metadata": {
            "created_at_utc": generated_at or datetime.now(UTC).isoformat(),
            "timestamp_excluded_from_payload_hash": True,
        },
    }


def write_baseline(root: Path, output: Path, *, generated_at: str | None = None) -> dict:
    document = build_document(root, generated_at=generated_at)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "docs/appendices/multiportfolio_v2_certification_closure/frozen_engine_baseline_v2.json"
        ),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    document = write_baseline(root, root / args.output)
    print(document["payload_sha256"])


if __name__ == "__main__":
    main()
