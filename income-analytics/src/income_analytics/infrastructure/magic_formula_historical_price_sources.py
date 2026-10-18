"""Targeted, auditable reads from official B3 COTAHIST archives."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from zipfile import BadZipFile, ZipFile


def _security_class_from_isin(isin: str) -> str | None:
    suffix = isin[7:11] if len(isin) == 12 else ""
    return {"CNOR": "ON", "CNPR": "PN", "CNPA": "PNA", "CNPB": "PNB"}.get(suffix)


def _security_class_from_specification(value: str) -> str | None:
    tokens = value.upper().split()
    return next((item for item in ("PNA", "PNB", "PN", "ON") if item in tokens), None)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_cotahist_archive(
    path: Path,
    securities: list[dict],
    *,
    source_url: str,
    retrieved_at: str | None = None,
) -> tuple[dict[str, list[dict]], dict]:
    """Stream one fixed-width ZIP, matching each identity by ticker OR ISIN."""
    identities = {
        f"{item['ticker']}|{item['isin']}": item
        for item in securities
        if item.get("ticker") and item.get("isin")
    }
    by_ticker: dict[str, list[str]] = {}
    by_isin: dict[str, list[str]] = {}
    for key, identity in identities.items():
        by_ticker.setdefault(identity["ticker"].strip().upper(), []).append(key)
        by_isin.setdefault(identity["isin"].strip().upper(), []).append(key)

    found = {key: [] for key in identities}
    scanned_records = 0
    try:
        with ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.upper().endswith(".TXT")]
            if len(members) != 1:
                raise ValueError("AMBIGUOUS_COTAHIST_MEMBER")
            member = members[0]
            with archive.open(member) as stream:
                for line_number, raw in enumerate(stream, start=1):
                    if raw[:2] != b"01":
                        continue
                    if len(raw.rstrip(b"\r\n")) != 245:
                        raise ValueError("INVALID_COTAHIST_RECORD_LENGTH")
                    scanned_records += 1
                    ticker = raw[12:24].decode("latin1").strip().upper()
                    isin = raw[230:242].decode("latin1").strip().upper()
                    keys = set(by_ticker.get(ticker, ())) | set(by_isin.get(isin, ()))
                    for key in keys:
                        specification = raw[39:49].decode("latin1").strip()
                        raw_price = raw[108:121].decode("ascii")
                        found[key].append(
                            {
                                "date": date.fromisoformat(raw[2:10].decode("ascii")).isoformat(),
                                "ticker": ticker,
                                "isin": isin,
                                "market_type": raw[24:27].decode("ascii"),
                                "specification": specification,
                                "security_class": _security_class_from_specification(specification),
                                "price_field": "PREULT",
                                "raw_price": raw_price,
                                "price": str(Decimal(raw_price) / Decimal(100)),
                                "source": path.name,
                                "source_dataset": "B3_COTAHIST",
                                "source_record_identifier": (
                                    f"{path.name}|{member}|line={line_number}"
                                ),
                                "ticker_match": ticker == identities[key]["ticker"].strip().upper(),
                                "isin_match": isin == identities[key]["isin"].strip().upper(),
                            }
                        )
    except BadZipFile as exc:
        raise ValueError("INVALID_COTAHIST_ZIP") from exc

    manifest = {
        "filename": path.name,
        "source": "B3",
        "download_reference_location": source_url,
        "year": int(path.stem[-4:]) if path.stem[-4:].isdigit() else None,
        "sha256": _sha256(path),
        "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat(),
        "zip_member": member,
        "scanned_records": scanned_records,
        "scan_complete": True,
        "identities": [
            {"ticker": item["ticker"], "isin": item["isin"]}
            for item in securities
            if item.get("ticker") and item.get("isin")
        ],
    }
    return found, manifest


def exact_price_candidate(identity: dict, records: list[dict], reference_date: str) -> dict:
    """Return a candidate only for exact date, ISIN/class and market 010."""
    if _security_class_from_isin(identity.get("isin", "")) != identity.get("security_class"):
        return {"status": "REJECTED", "reason": "CLASS_OR_ISIN_MISMATCH"}

    same_isin = [record for record in records if record.get("isin") == identity["isin"]]
    if not same_isin:
        return {"status": "MISSING", "reason": "NO_MATCHING_ISIN"}
    same_class = [
        record for record in same_isin if record.get("security_class") == identity["security_class"]
    ]
    if not same_class:
        return {"status": "REJECTED", "reason": "CLASS_MISMATCH"}
    exact_date = [record for record in same_class if record.get("date") == reference_date]
    if not exact_date:
        return {
            "status": "MISSING",
            "reason": "PRICE_EXISTS_BUT_POLICY_INCOMPATIBLE" if same_class else "NO_PRICE",
        }
    spot = [record for record in exact_date if record.get("market_type") == "010"]
    if not spot:
        return {"status": "MISSING", "reason": "PRICE_EXISTS_BUT_POLICY_INCOMPATIBLE"}
    if len(spot) != 1:
        return {"status": "AMBIGUOUS", "reason": "DUPLICATE_EXACT_CLOSE"}
    price = Decimal(spot[0]["price"])
    if price <= 0:
        return {"status": "REJECTED", "reason": "INVALID_NONPOSITIVE_PRICE"}
    return {"status": "CANDIDATE", "record": spot[0]}


def compare_source_prices(
    cotahist_price: str, other_price: str, *, tolerance: str = "0.01"
) -> dict:
    """Compare economically equivalent close fields without choosing a winner."""
    first, second = Decimal(cotahist_price), Decimal(other_price)
    absolute = abs(first - second)
    percent = (absolute / abs(first) * 100) if first else Decimal(0)
    return {
        "cotahist_price": str(first),
        "new_source_price": str(second),
        "abs_diff": str(absolute),
        "pct_diff": str(percent),
        "status": "CONSISTENT" if absolute <= Decimal(tolerance) else "SOURCE_CONFLICT",
    }


def build_price_provenance(
    identity: dict, record: dict, *, reference_date: str, retrieved_at: str
) -> dict:
    """Build HIGH-confidence candidate provenance after strict identity checks."""
    selected = exact_price_candidate(identity, [record], reference_date)
    if selected["status"] != "CANDIDATE":
        raise ValueError("HIGH_CONFIDENCE_EVIDENCE_REQUIREMENTS_NOT_MET")
    if not identity.get("issuer_confirmed") or not identity.get("identity_source"):
        raise ValueError("ISSUER_IDENTITY_PROVENANCE_REQUIRED")
    return {
        "ticker": identity["ticker"],
        "isin": identity["isin"],
        "security_class": identity["security_class"],
        "market_type": "010",
        "reference_date": reference_date,
        "price": record["price"],
        "source": "B3",
        "source_dataset": record["source_dataset"],
        "source_record_identifier": record["source_record_identifier"],
        "source_field": "PREULT",
        "retrieved_at": retrieved_at,
        "identity_confidence": "HIGH",
        "price_confidence": "HIGH",
    }
