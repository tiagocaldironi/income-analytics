"""Run in a fresh process after the audit writer exits; never execute ranking."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from income_analytics.application.historical_price import gap_analysis, resolve
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)


def run():
    output = Path("tmp/historical-price-phase3")
    expected = json.loads((output / "audited-universe.json").read_text(encoding="utf8"))
    repository = MagicFormulaUniverseRepository(Path("data/magic_formula/universe_snapshots.db"))
    actual = repository.read(expected["universe_snapshot_id"])
    parent = repository.read(actual["price_resolution_run"]["parent_id"])
    assert actual == expected
    assert actual["issuers"] == parent["issuers"]
    audit = actual["price_resolution_run"]
    archive = Path("data/cotahist") / audit["source_manifest"]["archive"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == audit["source_manifest"]["sha256"]
    coverage_started = perf_counter()
    assert audit["gap_analysis"] == gap_analysis(list(reversed(actual["issuers"])))
    coverage_seconds = perf_counter() - coverage_started
    assert len([i for i in audit["diagnostics"] if not i["control"]]) == 77
    assert len([i for i in audit["diagnostics"] if i["control"]]) == 5
    assert all(
        s["provider_output"] is not None
        for i in audit["diagnostics"]
        for s in i["securities"]
        if s["ticker"]
    )
    for issuer in audit["diagnostics"]:
        for resolution in issuer["securities"]:
            provider = resolution["provider_output"]
            if resolution["status"] == "RESOLVED":
                assert provider["found"]
                assert Decimal(provider["price"]) == Decimal(resolution["price"])
                assert provider["effective_date"] == resolution["effective_date"]
            elif resolution["reason_code"] in ("PRICE_RECORD_NOT_FOUND", "EFFECTIVE_DATE_GAP"):
                assert not provider["found"]
                assert provider["error"] == (
                    "Não foi encontrada cotação B3 válida nos sete dias anteriores "
                    "à data escolhida."
                )
    assert actual["ranking_status"] == "INACTIVE"
    assert actual["tool_status"] == "VALIDATION_REQUIRED"
    assert actual["coverage"]["independent_dimensions"] == dict(
        IDENTITY_RESOLVED=307,
        ACCOUNTING_READY=256,
        SECURITY_READY=269,
        CAPITAL_READY=276,
        MARKET_PRICE_READY=230,
        FULL_DATA_READY=178,
    )
    controls = [i for i in actual["issuers"] if i["canonical_status"] == "RESOLVED"]
    assert len(controls) == 5
    assert all(i["data_readiness_status"] == "FULL_DATA_READY" for i in controls)
    index = json.loads((output / "raw-index.json").read_text(encoding="utf8"))
    securities = {
        (i["issuer_id"], s["security_id"], s["source_reference"], s["share_class"]): s
        for i in actual["issuers"]
        for s in i["securities"]
    }
    resolution_started = perf_counter()
    for issuer in reversed(audit["diagnostics"]):
        for resolution in reversed(issuer["securities"]):
            expected_resolution = {k: v for k, v in resolution.items() if k != "provider_output"}
            assert (
                resolve(
                    securities[
                        (
                            issuer["issuer_id"],
                            resolution["security_id"],
                            resolution["security_source_reference"],
                            resolution["security_class"],
                        )
                    ],
                    list(reversed(index.get(resolution["ticker"], []))),
                    actual["reference_date"],
                )
                == expected_resolution
            )
    resolution_seconds = perf_counter() - resolution_started
    with TemporaryDirectory(dir=output) as temporary:
        independent = MagicFormulaUniverseRepository(Path(temporary) / "readback.db")
        independent.initialize()
        independent.save(actual)
        assert independent.read(actual["universe_snapshot_id"]) == actual
    report = dict(
        snapshot_id=actual["universe_snapshot_id"],
        parent_id=parent["universe_snapshot_id"],
        independent_process_readback="PASS",
        issuer_payload_financial_and_lineage_regression="PASS",
        all_gap_provider_comparisons="PASS",
        reordered_issuer_gap_analysis="PASS",
        new_process_reordered_price_resolution="PASS",
        independent_database_roundtrip="PASS",
        coverage_recomputation_duration_seconds=coverage_seconds,
        cached_price_policy_recomputation_duration_seconds=resolution_seconds,
        golden_controls=5,
        gaps_remaining=77,
        price_ready=230,
        full_data_ready=178,
        ranking_gate="BLOCKED",
        ranking_status="INACTIVE",
        gap_analysis=audit["gap_analysis"],
    )
    (output / "readback-report.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
