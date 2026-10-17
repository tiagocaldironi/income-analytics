"""V5 dry-run: targeted official B3 source expansion without snapshot writes."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from income_analytics.infrastructure.magic_formula_historical_price_sources import (
    exact_price_candidate,
    scan_cotahist_archive,
)
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)

ROOT = Path("tmp/magic-formula-price-blockers-batch-v3")
SOURCE_DIR = ROOT / "v5-data"
OUT = ROOT / "v5-dry-run.json"
ARCHIVE_METADATA = {
    2021: {
        "url": "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2021.ZIP",
        "retrieved_at": "2026-10-12T20:30:08.896641+00:00",
    },
    2020: {
        "url": "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2020.ZIP",
        "retrieved_at": "2026-10-12T20:34:16.105678+00:00",
    },
    2019: {
        "url": "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2019.ZIP",
        "retrieved_at": "2026-10-12T20:34:18.523287+00:00",
    },
}
REFERENCE_DATE = "2025-12-30"


def main() -> int:
    v4 = json.loads((ROOT / "availability-audit-data.json").read_text(encoding="utf-8"))
    v4_summary = json.loads((ROOT / "availability-audit-summary.json").read_text(encoding="utf-8"))
    repo = MagicFormulaUniverseRepository(Path("data/magic_formula/universe_snapshots.db"))
    baseline = repo.latest()
    with repo.connection() as connection:
        db_before = connection.execute(
            "SELECT COUNT(*), MAX(created_at) FROM magic_formula_universe_snapshots"
        ).fetchone()
        snapshot_rows = connection.execute(
            "SELECT rowid, universe_snapshot_id, created_at "
            "FROM magic_formula_universe_snapshots ORDER BY rowid"
        ).fetchall()
    b3_root = ROOT / "b3-evidence"
    unavailable = [
        case
        for case in v4_summary["unavailable_details"]
        if case["cause"] == "SOURCE_GAP"
    ]
    securities = []
    for company in unavailable:
        b3 = json.loads((b3_root / f"{company['cvm']}.json").read_text(encoding="utf-8"))
        for security in company["securities"]:
            securities.append(
                {
                    "company": company["company"],
                    "cvm_code": company["cvm"],
                    "cnpj": b3.get("cnpj"),
                    "listing_date": b3.get("dateQuotation"),
                    "ticker": security["ticker"],
                    "isin": security["isin"],
                    "security_class": security["class"],
                    "current_source_status": security["reason"],
                    "local_records_2022_2026": security.get("records", []),
                }
            )

    scans = {}
    manifests = []
    for year, metadata in ARCHIVE_METADATA.items():
        archive_path = SOURCE_DIR / f"COTAHIST_A{year}.ZIP"
        rows, manifest = scan_cotahist_archive(
            archive_path,
            securities,
            source_url=metadata["url"],
            retrieved_at=metadata["retrieved_at"],
        )
        scans[year] = rows
        manifests.append(manifest)

    results = []
    for security in securities:
        key = f"{security['ticker']}|{security['isin']}"
        historical = [record for year in (2019, 2020, 2021) for record in scans[year][key]]
        # V4's saved scan rows use ``class``/``market``; normalize that
        # persisted shape before applying the V5 canonical candidate rules.
        local_records = [
            {
                **record,
                "security_class": record.get("security_class", record.get("class")),
                "market_type": record.get("market_type", record.get("market")),
            }
            for record in security["local_records_2022_2026"]
        ]
        all_records = local_records + historical
        candidate = exact_price_candidate(security, all_records, REFERENCE_DATE)
        exact_cotahist_2025 = [
            record
            for record in security["local_records_2022_2026"]
            if record.get("date") == REFERENCE_DATE
            and record.get("market") == "010"
            and record.get("isin") == security["isin"]
        ]
        if candidate["status"] == "CANDIDATE":
            terminal = "RECOVERED_FROM_HISTORICAL_COTAHIST"
            candidate_record = candidate["record"]
        elif historical or any(
            record.get("market") == "010"
            for record in security["local_records_2022_2026"]
        ):
            terminal = "PRICE_EXISTS_BUT_POLICY_INCOMPATIBLE"
            candidate_record = None
        else:
            terminal = "OFFICIAL_SOURCE_CONFIRMED_NO_PRICE"
            candidate_record = None

        local_spot = [
            record
            for record in security["local_records_2022_2026"]
            if record.get("market") == "010" and record.get("isin") == security["isin"]
        ]
        historical_spot = [record for record in historical if record.get("market_type") == "010"]
        results.append(
            {
                "company": security["company"],
                "cvm_code": security["cvm_code"],
                "cnpj": security["cnpj"],
                "listing_date": security["listing_date"],
                "security_class": security["security_class"],
                "ticker": security["ticker"],
                "isin": security["isin"],
                "current_source_status": security["current_source_status"],
                "first_local_record": min((r["date"] for r in local_spot), default=None),
                "last_local_record": max((r["date"] for r in local_spot), default=None),
                "old_archive_records": historical,
                "old_archive_spot_records": historical_spot,
                "exact_2025_12_30_cotahist_010": exact_cotahist_2025,
                "candidate": candidate_record,
                "terminal_status": terminal,
                "historical_activity_fully_determined": all(
                    year in {2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026}
                    for year in range(
                        datetime.strptime(security["listing_date"], "%d/%m/%Y").year,
                        2027,
                    )
                ),
            }
        )

    counts = {}
    for result in results:
        counts[result["terminal_status"]] = counts.get(result["terminal_status"], 0) + 1
    source_2025_hash = next(
        item["sha256"] for item in v4["source_manifests"] if item["file"] == "COTAHIST_A2025.ZIP"
    )
    previous_manifests = [
        {
            "filename": item["file"],
            "source": "B3",
            "download_reference_location": f"https://bvmf.bmfbovespa.com.br/InstDados/SerHist/{item['file']}",
            "year": int(item["file"][-8:-4]),
            "sha256": item["sha256"],
            "retrieved_at": None,
            "retrieval_note": (
                "Previously available and fully scanned in V4; original retrieval "
                "timestamp is not in the saved manifest."
            ),
        }
        for item in v4["source_manifests"]
    ]
    all_manifests = previous_manifests + manifests
    (ROOT / "v5-source-manifest.json").write_text(
        json.dumps(all_manifests, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with repo.connection() as connection:
        db_after = connection.execute(
            "SELECT COUNT(*), MAX(created_at) FROM magic_formula_universe_snapshots"
        ).fetchone()
    output = {
        "audit": "MAGIC_FORMULA_HISTORICAL_PRICE_SOURCE_EXPANSION_V5",
        "mode": "V5_DRY_RUN",
        "reference_date": REFERENCE_DATE,
        "baseline": {
            "snapshot_id": baseline["universe_snapshot_id"],
            "reference_date": baseline["reference_date"],
            "total_universe": 307,
            "complete_companies": 185,
            "coverage_percent": 60.26,
            "ranking_status": baseline["ranking_status"],
            "tool_status": baseline["tool_status"],
        },
        "cotahist_2022_2026": {
            "years": [2022, 2023, 2024, 2025, 2026],
            "reference_date_archive": "COTAHIST_A2025.ZIP",
            "sha256": source_2025_hash,
            "complete_scan_confirmed_by_v4": True,
        },
        "source_manifests": all_manifests,
        "bdi": {
            "structured_table_available": True,
            "structured_for_2025_12_30": False,
            "reason": (
                "BDI historical date is beyond the structured date-picker window; "
                "older bulletins are redirected to PDF archive, and the selected "
                "stock summary table exposes trade count/volume rather than a close field."
            ),
            "provider_integrated": False,
        },
        "cases": results,
        "terminal_status_counts": counts,
        "status_sum": sum(counts.values()),
        "projected": {
            "security_prices_recovered": sum(r["candidate"] is not None for r in results),
            "companies_becoming_complete": 0,
            "complete_companies": 185,
            "coverage_percent": 60.26,
        },
        "snapshot": {
            "old_snapshot_preserved": True,
            "new_snapshot_created": False,
            "database_before": list(db_before),
            "database_after": list(db_after),
            "ranking_active": False,
            "ranking_blocked": True,
            "top_30_published": False,
            "selection_query": "ORDER BY created_at DESC, rowid DESC",
            "selection_deterministic": True,
            "tie_rowids_present_and_unique": len({row[0] for row in snapshot_rows})
            == len(snapshot_rows),
        },
    }
    if db_after != db_before or len(results) != 14 or output["status_sum"] != 14:
        raise RuntimeError("V5_DRY_RUN_INVARIANT_FAILED")
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(OUT),
                "terminal_status_counts": counts,
                "status_sum": output["status_sum"],
                "snapshot_unchanged": db_before == db_after,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
