# ruff: noqa: E501
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .provider import BrapiPaidIncomeProvider

TICKERS = {"PETR4": "Stock control", "TASA4": "Stock", "KLBN11": "Unit", "CMIG4": "Stock", "GGRC11": "FII", "HSML11": "FII"}


def main() -> None:
    provider = BrapiPaidIncomeProvider()
    end = date.today()
    start = date(end.year - 2, end.month, end.day)
    report = {"provider": "brapi", "endpoint": provider.endpoint, "authentication": "BRAPI_TOKEN configured" if provider._token else "without token", "window": [str(start), str(end)], "queries": []}
    for ticker, asset_type in TICKERS.items():
        response = provider.get_paid_income(ticker, start, end)
        paid = response.events
        row = {"ticker": ticker, "asset_type": asset_type, "http_status": response.status_code, "provider_result": response.result, "detail": response.detail, "elapsed_ms": response.elapsed_ms, "events_found": len(paid), "oldest_event": str(min((x.payment_date for x in paid), default="")), "newest_event": str(max((x.payment_date for x in paid), default="")), "has_record_date": any(x.record_date for x in paid), "has_payment_date": bool(paid), "has_amount": bool(paid), "events": [{**asdict(x), "amount_per_unit": str(x.amount_per_unit), "income_type": x.income_type} for x in paid[:8]]}
        report["queries"].append(row)
        print(f"{ticker:<6} {response.result:<20} {len(paid):>3} eventos HTTP {response.status_code}")
    output = Path("tmp/paid-income-spike")
    output.mkdir(parents=True, exist_ok=True)
    (output / "paid_income_spike_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
