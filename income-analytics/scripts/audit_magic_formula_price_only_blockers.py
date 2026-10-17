"""Produce a reproducible, evidence-only inventory of price-only blockers."""

import hashlib
import json
import re
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from zipfile import ZipFile

from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "tmp/historical-price-phase3/audited-universe.json"
OUTPUT = ROOT / "tmp/price-recovery-phase1/price-only-blockers.json"
ARCHIVE = ROOT / "data/cotahist/COTAHIST_A2025.ZIP"


def normalize(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def official_daily_names(reference_date: str) -> dict[str, set[str]]:
    names: dict[str, set[str]] = {}
    requested = reference_date.replace("-", "").encode()
    start = (date.fromisoformat(reference_date) - timedelta(days=7)).strftime("%Y%m%d").encode()
    with ZipFile(ARCHIVE) as archive:
        member = next(name for name in archive.namelist() if name.upper().endswith(".TXT"))
        with archive.open(member) as records:
            for raw in records:
                if raw[:2] != b"01" or not start <= raw[2:10] <= requested or raw[24:27] != b"010":
                    continue
                name = raw[27:39].decode("latin1").strip()
                ticker = raw[12:24].decode("latin1").strip()
                if name and ticker and not ticker.endswith("F"):
                    names.setdefault(name, set()).add(ticker)
    return names


def candidate_names(display_name: str, names: dict[str, set[str]]) -> list[dict]:
    target = normalize(display_name)
    ranked = sorted(
        names,
        key=lambda name: (-SequenceMatcher(None, target, normalize(name)).ratio(), name),
    )[:3]
    return [
        {
            "cotahist_short_name": name,
            "candidate_tickers": sorted(names[name]),
            "similarity": round(SequenceMatcher(None, target, normalize(name)).ratio(), 4),
            "status": "UNVERIFIED_DISCOVERY_LEAD",
        }
        for name in ranked
    ]


def classification(security: dict, reference_date: str) -> tuple[str, str]:
    ticker = security["ticker"] or ""
    records = security["cotahist_records"]
    if not re.fullmatch(r"[A-Z]{4}[0-9]{1,2}", ticker):
        return "UNKNOWN", "NON_STANDARD_TICKER_REQUIRES_IDENTITY_EVIDENCE"
    if records:
        window_start = (date.fromisoformat(reference_date) - timedelta(days=7)).isoformat()
        historical = [row for row in records if row["effective_date"] <= reference_date]
        if any(row["effective_date"] >= window_start for row in historical):
            return "AVAILABLE", "RECORD_IN_APPROVED_WINDOW"
        if historical:
            return "SOURCE_MISSING_DATE", "NO_TRADE_IN_APPROVED_WINDOW"
    return "UNKNOWN", "NO_PROVEN_HISTORICAL_TICKER_MAPPING"


def run() -> None:
    document = json.loads(INPUT.read_text(encoding="utf8"))
    persisted = MagicFormulaUniverseRepository(
        ROOT / "data/magic_formula/universe_snapshots.db"
    ).latest()
    if persisted != document:
        raise ValueError("BASELINE_SNAPSHOT_MISMATCH")
    dimensions = document["coverage"]["independent_dimensions"]
    if dimensions["FULL_DATA_READY"] != 178 or dimensions["MARKET_PRICE_READY"] != 230:
        raise ValueError("BASELINE_COVERAGE_MISMATCH")
    raw_index = json.loads(
        (ROOT / "tmp/historical-price-phase3/raw-index.json").read_text(encoding="utf8")
    )
    reference_date = document["reference_date"]
    names = official_daily_names(reference_date)
    blockers = []
    for issuer in document["issuers"]:
        market = issuer["market_readiness"]
        if not (
            issuer["methodology_eligibility"] == "ELIGIBLE"
            and issuer["accounting_readiness"]["ready"]
            and market["security_ready"]
            and market["capital_ready"]
            and not market["price_ready"]
        ):
            continue
        securities = []
        for security in issuer["securities"]:
            records = raw_index.get(security["ticker"], [])
            enriched = {
                **security,
                "cotahist_records": records,
                "expected_ticker": security["ticker"],
                "current_ticker": None,
                "historical_ticker": security["ticker"] if records else None,
                "identity_mapping_verified": False,
                "cotahist_record_count": len(records),
                "cotahist_last_date": max((row["effective_date"] for row in records), default=None),
            }
            category, reason = classification(enriched, reference_date)
            enriched["initial_category"] = category
            enriched["initial_reason"] = reason
            securities.append(enriched)
        categories = sorted(
            {
                security["initial_category"]
                for security in securities
                if security["initial_category"] != "AVAILABLE"
            }
        )
        category = "SOURCE_MISSING_DATE" if categories == ["SOURCE_MISSING_DATE"] else "UNKNOWN"
        blockers.append(
            {
                "issuer_id": issuer["issuer_id"],
                "cvm_code": issuer["cvm_code"],
                "cnpj": issuer["cnpj"],
                "display_name": issuer["display_name"],
                "reference_date": reference_date,
                "price_window_start": (
                    date.fromisoformat(reference_date) - timedelta(days=7)
                ).isoformat(),
                "price_window_end": reference_date,
                "current_source": "B3_COTAHIST_A2025",
                "accounting_status": "READY",
                "security_status": "READY",
                "capital_status": "READY",
                "price_status": "NOT_READY",
                "source_gap_reason": "NO_REFERENCE_PRICE",
                "initial_categories": categories,
                "primary_category": category,
                "classification_scope": "CURRENT_TICKERS_IN_FROZEN_ANNUAL_ARCHIVE",
                "recovered": False,
                "official_cotahist_name_leads": candidate_names(issuer["display_name"], names),
                "securities": securities,
            }
        )
    assert len(blockers) == 38
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {
                "reference_date": reference_date,
                "price_policy_version": "MAGIC_FORMULA_HISTORICAL_PRICE_V1",
                "source_archive": ARCHIVE.name,
                "source_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
                "baseline_snapshot_id": document["universe_snapshot_id"],
                "baseline_sha256": hashlib.sha256(INPUT.read_bytes()).hexdigest(),
                "category_counts": {
                    category: sum(b["primary_category"] == category for b in blockers)
                    for category in sorted({b["primary_category"] for b in blockers})
                },
                "blocker_count": len(blockers),
                "blockers": blockers,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf8",
    )
    print(f"Wrote {len(blockers)} blockers to {OUTPUT}")


if __name__ == "__main__":
    run()
