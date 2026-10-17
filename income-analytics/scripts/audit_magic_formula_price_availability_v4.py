"""Read-only scan of pinned B3 COTAHIST archives for V4 audit subjects."""

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

ROOT = Path("tmp/magic-formula-price-blockers-batch-v3")
SOURCE = ROOT / "dry-run-4/candidate.json"
OUTPUT = ROOT / "availability-audit-data.json"


def scan():
    candidate = json.loads(SOURCE.read_text(encoding="utf-8"))
    cases = [
        c
        for c in candidate["identity_recovery_run"]["case_results"]
        if c["terminal_status"]
        in {"IDENTITY_CONFIRMED_PRICE_UNAVAILABLE", "NO_TRADE_ON_REFERENCE_DATE"}
    ]
    identities = []
    for case in cases:
        for attempt in case["resolution_attempts"]:
            identity = attempt.get("selected_identity")
            if identity:
                identities.append(
                    {
                        "cvm": case["cvm_code"],
                        "company": case["company"],
                        "prior_status": case["terminal_status"],
                        "reason": attempt.get("price_lookup_result"),
                        "ticker": identity["ticker"],
                        "isin": identity["isin"],
                        "class": identity["class"],
                    }
                )
    tickers = {item["ticker"] for item in identities}
    isins = {item["isin"] for item in identities}
    rows = defaultdict(list)
    trading_dates = set()
    manifests = []
    files = sorted(Path("data/cotahist").glob("COTAHIST_A20*.ZIP"))
    for path in files:
        year = int(path.stem[-4:])
        print("Scanning", path.name, flush=True)
        manifests.append(
            {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        )
        with ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.upper().endswith(".TXT")]
            if len(members) != 1:
                manifests[-1]["scan_error"] = "AMBIGUOUS_MEMBER"
                continue
            member = members[0]
            with archive.open(member) as stream:
                for line_number, raw in enumerate(stream, 1):
                    if raw[:2] != b"01":
                        continue
                    date_text = raw[2:10].decode("ascii")
                    effective_date = f"{date_text[:4]}-{date_text[4:6]}-{date_text[6:8]}"
                    market = raw[24:27].decode("ascii")
                    if year == 2025 and market == "010":
                        trading_dates.add(effective_date)
                    ticker = raw[12:24].decode("latin1").strip()
                    isin = raw[230:242].decode("latin1").strip()
                    if ticker not in tickers and isin not in isins:
                        continue
                    raw_price = raw[108:121].decode("ascii")
                    rows[(ticker, isin)].append(
                        {
                            "date": effective_date,
                            "ticker": ticker,
                            "isin": isin,
                            "market": market,
                            "bdi": raw[10:12].decode("ascii"),
                            "security_type": raw[39:49].decode("latin1").strip(),
                            "price": str(int(raw_price) / 100),
                            "raw_price": raw_price,
                            "source": f"{path.name}|{member}|line={line_number}",
                        }
                    )
    items = []
    for identity in identities:
        matching = [
            record
            for (ticker, isin), records in rows.items()
            if isin == identity["isin"] or ticker == identity["ticker"]
            for record in records
        ]
        items.append({**identity, "records": sorted(matching, key=lambda record: record["date"])})
    result = {
        "reference_date_for_policy_simulation": "2025-12-30",
        "source_manifests": manifests,
        "trading_dates_2025": sorted(trading_dates),
        "cases": cases,
        "items": items,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in items:
        records = [record for record in item["records"] if record["market"] == "010"]
        print(
            item["cvm"],
            item["ticker"],
            item["isin"],
            len(records),
            (records[0]["date"], records[-1]["date"]) if records else "NO_MARKET_010",
            flush=True,
        )
    print(
        "RESULT",
        OUTPUT,
        "cases",
        len(cases),
        "securities",
        len(items),
        "unique B3 trading dates 2025",
        len(trading_dates),
        flush=True,
    )


if __name__ == "__main__":
    scan()
