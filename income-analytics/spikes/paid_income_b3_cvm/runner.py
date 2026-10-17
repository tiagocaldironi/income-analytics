"""Run the reproducible evidence check for SPIKE 2."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .provider import CvmFiiMonthlyProvider

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tmp" / "paid-income-b3-cvm"
OUT = RAW / "report.json"


def main() -> None:
    provider = CvmFiiMonthlyProvider(RAW)
    start, end = date(2024, 8, 1), date(2026, 8, 31)
    evidence = {
        ticker: [
            {
                "reference_date": item.reference_date.isoformat(),
                "dividend_yield_month": str(item.dividend_yield_month),
                "amortization_month": str(item.amortization_month),
            }
            for item in provider.monthly_evidence(ticker, start, end)
        ]
        for ticker in ("GGRC11", "HSML11")
    }
    OUT.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(OUT)
    for ticker, rows in evidence.items():
        print(f"{ticker}: {len(rows)} observações mensais")


if __name__ == "__main__":
    main()
