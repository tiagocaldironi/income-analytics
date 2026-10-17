"""Replay a pinned official record and identity documents without any network."""

import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from income_analytics.application.historical_security_identity import recover_price


def test_versioned_official_identity_and_price_recovery():
    folder = Path(__file__).resolve().parents[1] / "fixtures/cvm/price_identity_v1"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf8"))
    for filename, expected in manifest["files"].items():
        assert hashlib.sha256((folder / filename).read_bytes()).hexdigest() == expected
    issuer, proof, current = [
        json.loads((folder / filename).read_text(encoding="utf8"))
        for filename in ("issuer-before.json", "offer-identity.json", "current-directory.json")
    ]
    assert (
        hashlib.sha256((folder / "offer-notice.pdf").read_bytes()).hexdigest()
        == proof["source_sha256"]
    )
    raw = (folder / "cotahist-record.txt").read_bytes()
    record = {
        "ticker": raw[12:24].decode().strip(),
        "isin": raw[230:242].decode().strip(),
        "market": raw[24:27].decode(),
        "effective_date": date.fromisoformat(raw[2:10].decode()).isoformat(),
        "price": str(Decimal(raw[108:121].decode()) / 100),
        "raw_price": raw[108:121].decode(),
        "currency": raw[52:56].decode().strip(),
        "source_reference": manifest["source_reference"],
    }
    result = recover_price(issuer, proof, current, [record], manifest["reference_date"])
    assert result["securities"][0]["price"] == "5.45"
    assert result["securities"][0]["effective_market_date"] == "2025-12-30"
    assert result["accounting_readiness"] == issuer["accounting_readiness"]
    assert (
        result["market_readiness"]["normalized_outstanding_by_class"]
        == issuer["market_readiness"]["normalized_outstanding_by_class"]
    )
    assert result["canonical_ranking_eligible"] is False
