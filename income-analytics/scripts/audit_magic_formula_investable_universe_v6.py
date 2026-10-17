"""Read-only V6 investable-universe and liquidity audit; never calculates ranks."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median
from zipfile import ZipFile

from income_analytics.application.magic_formula_investable_universe import (
    POLICY,
    company_liquidity_scenario,
    liquidity_scenario,
    listing_status,
    market_type_is_eligible,
    normalized_sector,
    primary_status,
    publication_guard,
    structural_decision,
)
from income_analytics.application.magic_formula_investable_universe import (
    legacy_user_policy_decision as user_policy_decision,
)

ROOT = Path("tmp/magic-formula-investable-v6")
DATABASE = Path("data/magic_formula/universe_snapshots.db")
REFERENCE_DATE = "2025-12-31"
PRICE_DATE = "2025-12-30"
UNRESOLVED_CVM = {"020575", "024317", "025844", "011231", "026700"}
UNRESOLVED_NAMES = {
    "020575": "JBS S.A.",
    "024317": "ZAMP S.A.",
    "025844": "Tegra Incorporadora S.A.",
    "011231": "Tekno S.A.",
    "026700": "Eurofarma Laboratórios S.A.",
}
ABSOLUTE_CAP_THRESHOLDS = {
    "R$500M": Decimal("500000000"),
    "R$1B": Decimal("1000000000"),
    "R$5B": Decimal("5000000000"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_path(year: int) -> Path:
    primary = Path(f"data/cotahist/COTAHIST_A{year}.ZIP")
    if primary.exists():
        return primary
    return Path(f"tmp/magic-formula-price-blockers-batch-v3/v5-data/COTAHIST_A{year}.ZIP")


def percentile(values: list[Decimal], pct: Decimal) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * pct
    low, high = int(pos), min(int(pos) + 1, len(ordered) - 1)
    fraction = pos - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


def parse_decimal_field(raw: bytes, scale: Decimal = Decimal(100)) -> Decimal | None:
    try:
        return Decimal(raw.decode("ascii").strip()) / scale
    except InvalidOperation:
        return None
    except UnicodeDecodeError:
        return None


def scan_archives(issuers: list[dict], years: range) -> tuple[dict, dict, list[dict]]:
    """Scan exact ticker+ISIN identities; only 2025 data feeds 30/60/90 metrics."""
    identity_map: dict[str, list[tuple[str, str]]] = defaultdict(list)
    security_by_key = {}
    for issuer in issuers:
        for index, security in enumerate(issuer["securities"]):
            ticker = str(security.get("ticker") or "").upper().strip()
            isin = str(security.get("isin") or "").upper().strip()
            key = f"{issuer['cvm_code']}|{index}|{ticker}|{isin}"
            security_by_key[key] = (issuer, security)
            if re.fullmatch(r"[A-Z0-9]{4,6}", ticker) and isin:
                identity_map[ticker].append((isin, key))

    trades: dict[str, dict[str, Decimal]] = {key: {} for key in security_by_key}
    sessions_2025: set[str] = set()
    sessions_all: set[str] = set()
    manifests = []
    for year in years:
        path = archive_path(year)
        if not path.exists():
            raise FileNotFoundError(f"MISSING_COTAHIST_A{year}")
        records = 0
        with ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.upper().endswith(".TXT")]
            if len(members) != 1:
                raise ValueError(f"AMBIGUOUS_COTAHIST_MEMBER:{path.name}")
            member = members[0]
            with archive.open(member) as stream:
                for line_number, raw in enumerate(stream, start=1):
                    if raw[:2] != b"01":
                        continue
                    if len(raw.rstrip(b"\r\n")) != 245:
                        raise ValueError(f"INVALID_COTAHIST_ROW:{path.name}:{line_number}")
                    records += 1
                    if not market_type_is_eligible(raw[24:27].decode("ascii")):
                        continue
                    date_value = raw[2:10].decode("ascii")
                    day = f"{date_value[:4]}-{date_value[4:6]}-{date_value[6:8]}"
                    if day <= PRICE_DATE:
                        sessions_all.add(day)
                    ticker = raw[12:24].decode("latin1").strip().upper()
                    if year == 2025 and day <= PRICE_DATE:
                        sessions_2025.add(day)
                    targets = identity_map.get(ticker, [])
                    if not targets:
                        continue
                    isin = raw[230:242].decode("latin1").strip().upper()
                    matching = [key for expected_isin, key in targets if expected_isin == isin]
                    if not matching:
                        continue
                    volume = parse_decimal_field(raw[170:188])
                    if volume is None:
                        raise ValueError(f"INVALID_VOLTOT:{path.name}:{line_number}")
                    for key in matching:
                        # COTAHIST gives one daily security line; sum defensively if
                        # a file has multiple eligible records for a ticker/date.
                        trades[key][day] = trades[key].get(day, Decimal(0)) + volume
        manifests.append(
            {
                "filename": path.name,
                "source": "B3 COTAHIST (existing local archive)",
                "reference": str(path),
                "year": year,
                "sha256": sha256(path),
                "retrieved_at": "not retained for existing archive",
                "scanned_quote_records": records,
                "complete_scan": True,
            }
        )
    return (
        trades,
        {
            "sessions_2025": sorted(sessions_2025),
            "sessions_all": sorted(sessions_all),
        },
        manifests,
    )


def security_metrics(
    issuers: list[dict],
    trades: dict,
    sessions: list[str],
    sessions_all: list[str],
) -> dict[str, dict]:
    result = {}
    for issuer in issuers:
        for index, security in enumerate(issuer["securities"]):
            ticker = str(security.get("ticker") or "").upper().strip()
            isin = str(security.get("isin") or "").upper().strip()
            key = f"{issuer['cvm_code']}|{index}|{ticker}|{isin}"
            history = trades.get(key, {})
            valid_identity = bool(re.fullmatch(r"[A-Z0-9]{4,6}", ticker) and isin)
            metrics = None
            if valid_identity:
                metrics = {
                    **_liquidity_metrics(sessions, history, PRICE_DATE, sessions_all),
                    "metric_status": "OBSERVED_NO_010_TRADE_2019_2025"
                    if not history
                    else "OBSERVED",
                }
            result[key] = metrics
    return result


def _liquidity_metrics(
    sessions: list[str],
    history: dict[str, Decimal],
    reference: str,
    sessions_all: list[str] | None = None,
) -> dict:
    sessions = [day for day in sessions if day <= reference]
    history = {day: volume for day, volume in history.items() if day <= reference}
    last_trade = max(history, default=None)
    result = {"last_trade_date": last_trade}
    for window in (30, 60, 90):
        sample = sessions[-window:]
        traded = sum(day in history for day in sample)
        volumes = [history.get(day, Decimal(0)) for day in sample]
        result[f"trading_days_{window}d"] = len(sample)
        result[f"days_with_trade_{window}d"] = traded
        result[f"traded_days_ratio_{window}d"] = Decimal(traded) / len(sample) if sample else None
        result[f"median_daily_financial_volume_{window}d"] = (
            Decimal(str(median(volumes))) if volumes else None
        )
    if last_trade:
        result["calendar_days_since_last_trade"] = (
            date.fromisoformat(reference) - date.fromisoformat(last_trade)
        ).days
        all_sessions = [day for day in (sessions_all or sessions) if last_trade < day <= reference]
        result["trading_days_since_last_trade"] = len(all_sessions)
        result["last_trade_search_start"] = "2019-01-01"
        result["last_trade_exact_in_checked_span"] = True
    else:
        result["calendar_days_since_last_trade"] = None
        result["trading_days_since_last_trade"] = None
        result["last_trade_search_start"] = "2019-01-01"
        result["last_trade_exact_in_checked_span"] = False
    return result


def company_scenario(issuer: dict, metrics_by_security: dict, scenario: str) -> str:
    states = []
    for index, security in enumerate(issuer["securities"]):
        ticker = str(security.get("ticker") or "").upper().strip()
        isin = str(security.get("isin") or "").upper().strip()
        key = f"{issuer['cvm_code']}|{index}|{ticker}|{isin}"
        states.append(metrics_by_security.get(key))
    if issuer["cvm_code"] in UNRESOLVED_CVM and scenario != "L0":
        return "REVIEW"
    return company_liquidity_scenario(states, scenario)


def issuer_market_cap(issuer: dict) -> tuple[Decimal | None, str]:
    market = issuer["market_readiness"]
    normalized = market.get("normalized_outstanding_by_class")
    if (
        not market.get("capital_ready")
        or market.get("unit_resolution_policy_version") != "MAGIC_FORMULA_HISTORICAL_SHARES_UNIT_V1"
        or not isinstance(normalized, dict)
    ):
        return None, "CAPITAL_OR_SHARE_UNIT_UNRESOLVED"
    prices = issuer["securities"]
    total = Decimal(0)
    counted = 0
    for share_class, outstanding in normalized.items():
        shares = parse_json_decimal(outstanding)
        if shares is None or shares < 0:
            return None, "INVALID_SHARE_QUANTITY"
        if shares == 0:
            continue
        matches = [
            security
            for security in prices
            if security.get("share_class") == share_class
            and security.get("price_status") == "AVAILABLE"
            and security.get("price") is not None
            and security.get("effective_market_date")
            and 0
            <= (
                date.fromisoformat(PRICE_DATE)
                - date.fromisoformat(security["effective_market_date"])
            ).days
            <= 7
        ]
        if len(matches) != 1:
            return None, "CLASS_PRICE_MISSING_OR_AMBIGUOUS"
        total += shares * Decimal(str(matches[0]["price"]))
        counted += 1
    if counted == 0:
        return None, "NO_ISSUED_SHARE_CLASSES"
    return total, "RESOLVED"


def parse_json_decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def scenario_summary(issuers: list[dict], metrics_by_security: dict, data_complete: dict) -> dict:
    summary = {}
    for scenario in ("L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"):
        states = {
            issuer["cvm_code"]: company_scenario(issuer, metrics_by_security, scenario)
            for issuer in issuers
        }
        passes = [code for code, state in states.items() if state == "PASS"]
        fails = [code for code, state in states.items() if state == "FAIL"]
        reviews = [code for code, state in states.items() if state == "REVIEW"]
        complete = sum(data_complete.get(code, False) for code in passes)
        retained = len(passes) + len(reviews)
        retained_complete = complete + sum(data_complete.get(code, False) for code in reviews)
        summary[scenario] = {
            "investable_confirmed_pass": len(passes),
            "liquidity_scenario_fail_review_only": len(fails),
            "liquidity_review_unknown": len(reviews),
            "complete_among_confirmed_pass": complete,
            "blocked_among_confirmed_pass": len(passes) - complete,
            "coverage_confirmed_pass": pct(complete, len(passes)),
            "coverage_if_review_retained": pct(retained_complete, retained),
            "review_retained_denominator": retained,
            "states_by_cvm": states,
        }
    return summary


def pct(numerator: int, denominator: int) -> str | None:
    return f"{100 * numerator / denominator:.2f}%" if denominator else None


def quantile_summary(entries: list[dict], field: str) -> dict:
    values = [entry[field] for entry in entries if entry.get(field) is not None]
    result = {"n": len(values), "total": len(entries)}
    for key, q in (
        ("p10", Decimal("0.10")),
        ("p25", Decimal("0.25")),
        ("p50", Decimal("0.50")),
        ("p75", Decimal("0.75")),
        ("p90", Decimal("0.90")),
    ):
        value = percentile(values, q)
        result[key] = str(value) if value is not None else None
    return result


def run() -> dict:
    ROOT.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(f"file:{DATABASE.resolve().as_posix()}?mode=ro", uri=True)
    row = connection.execute(
        "SELECT universe_snapshot_id,created_at,document_json "
        "FROM magic_formula_universe_snapshots "
        "ORDER BY created_at DESC,rowid DESC LIMIT 1"
    ).fetchone()
    connection.close()
    snapshot_id, created_at, raw_doc = row
    snapshot = json.loads(raw_doc)
    source_candidates = snapshot["issuers"]
    # The V5 baseline's 307 is the already-structurally-classified universe.
    # The source snapshot has 360 candidates: 35 finance exclusions and 18 review.
    raw = [
        issuer for issuer in source_candidates if issuer["methodology_eligibility"] == "ELIGIBLE"
    ]
    if len(raw) != 307:
        raise RuntimeError(f"RAW_BASELINE_CHANGED:{len(raw)}")
    v4_summary = json.loads(
        Path("tmp/magic-formula-price-blockers-batch-v3/availability-audit-summary.json").read_text(
            encoding="utf-8"
        )
    )
    audit_root = Path("tmp/magic-formula-price-blockers-batch-v3")
    v4_data = json.loads((audit_root / "availability-audit-data.json").read_text(encoding="utf-8"))
    v5 = json.loads((audit_root / "v5-dry-run.json").read_text(encoding="utf-8"))
    audited_identities = {}
    for item in v4_data["items"]:
        cvm = str(item["cvm"]).zfill(6)
        audited_identities[(cvm, item["ticker"].upper())] = {
            "isin": item["isin"],
            "class": item["class"],
            "source": "V4 confirmed security identity",
        }
    for item in v5["cases"]:
        cvm = str(item["cvm_code"]).zfill(6)
        audited_identities[(cvm, item["ticker"].upper())] = {
            "isin": item["isin"],
            "class": item["security_class"],
            "source": "V5 confirmed security identity",
        }
    by_cvm_source = {str(item["cvm_code"]).zfill(6): item for item in raw}
    for (cvm, ticker), identity in audited_identities.items():
        issuer = by_cvm_source.get(cvm)
        if issuer is None:
            continue
        existing = any(
            str(security.get("ticker") or "").upper() == ticker
            and str(security.get("isin") or "").upper() == identity["isin"].upper()
            for security in issuer["securities"]
        )
        if not existing:
            issuer["securities"].append(
                {
                    "ticker": ticker,
                    "isin": identity["isin"],
                    "share_class": identity["class"],
                    "security_status": "RESOLVED",
                    "price_status": "DATA_GAP",
                    "effective_market_date": None,
                    "liquidity_identity_source": identity["source"],
                }
            )
    years = range(2019, 2026)
    years = range(2019, 2026)
    trades, session_result, manifests = scan_archives(raw, years)
    sessions = session_result["sessions_2025"]
    sessions_all = session_result["sessions_all"]
    if len(sessions) != 250 or PRICE_DATE not in sessions:
        raise RuntimeError(f"UNEXPECTED_2025_TRADING_SESSIONS:{len(sessions)}")
    metrics_by_security = security_metrics(raw, trades, sessions, sessions_all)
    data_complete = {}
    company_records = []
    security_records = []
    company_metrics = {}
    for issuer in raw:
        cvm = str(issuer["cvm_code"]).zfill(6)
        structure = structural_decision(issuer)
        user = user_policy_decision(issuer)
        listing = listing_status(issuer["securities"], REFERENCE_DATE)
        rows = []
        for index, security in enumerate(issuer["securities"]):
            ticker = str(security.get("ticker") or "").upper().strip()
            isin = str(security.get("isin") or "").upper().strip()
            key = f"{cvm}|{index}|{ticker}|{isin}"
            metrics = metrics_by_security[key]
            scenario_states = {
                scenario: liquidity_scenario(metrics, scenario)
                for scenario in ("L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7")
            }
            security_records.append(
                {
                    "cvm_code": cvm,
                    "company": issuer["display_name"],
                    "sector": issuer.get("economic_sector"),
                    "ticker": ticker,
                    "isin": isin,
                    "liquidity_identity_source": security.get(
                        "liquidity_identity_source", "snapshot security record"
                    ),
                    "share_class": security.get("share_class"),
                    "security_status": security.get("security_status"),
                    "price_status": security.get("price_status"),
                    "price_effective_date": security.get("effective_market_date"),
                    **(metrics or {"metric_status": "IDENTITY_OR_TICKER_UNRESOLVED"}),
                    **{f"scenario_{k}": v for k, v in scenario_states.items()},
                }
            )
            rows.append(metrics)
        # Company-level scenarios mean at least one identified class can be bought;
        # volume is never summed across share classes.
        representative = max(
            (m for m in rows if m is not None),
            key=lambda m: (
                m.get("traded_days_ratio_30d") or Decimal(0),
                m.get("median_daily_financial_volume_30d") or Decimal(0),
            ),
            default=None,
        )
        company_metrics[cvm] = representative
        complete = (
            issuer["data_readiness_status"] == "FULL_DATA_READY" and cvm not in UNRESOLVED_CVM
        )
        data_complete[cvm] = complete
        scenario_states = {
            scenario: company_scenario(issuer, metrics_by_security, scenario)
            for scenario in ("L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7")
        }
        final = primary_status(
            structural=structure,
            user_policy=user,
            data_complete=complete,
            liquidity_metrics=representative,
            identity_unresolved=cvm in UNRESOLVED_CVM,
        )
        market_cap, market_cap_status = issuer_market_cap(issuer)
        company_records.append(
            {
                "cvm_code": cvm,
                "cnpj": issuer.get("cnpj"),
                "company": issuer["display_name"],
                "sector": issuer.get("economic_sector"),
                "base_sector": normalized_sector(issuer.get("economic_sector")),
                "listing_status": listing,
                "structural_status": structure["status"],
                "structural_rule": structure["rule"],
                "user_policy_status": user["status"],
                "user_policy_rule": user["rule"],
                "user_policy_exception": user.get("exception"),
                "primary_status": final,
                "identity_unresolved_v4": cvm in UNRESOLVED_CVM,
                "data_status": "COMPLETE" if complete else "BLOCKED",
                "data_reason_codes": ";".join(issuer["data_reason_codes"]),
                "securities": ";".join(
                    f"{s.get('ticker')}:{s.get('share_class')}:{s.get('isin')}"
                    for s in issuer["securities"]
                ),
                "market_cap": str(market_cap) if market_cap is not None else None,
                "market_cap_status": market_cap_status,
                "liquidity_representative_ticker": next(
                    (
                        r["ticker"]
                        for r in security_records[::-1]
                        if r["cvm_code"] == cvm
                        and company_metrics[cvm] is not None
                        and r.get("traded_days_ratio_30d")
                        == company_metrics[cvm].get("traded_days_ratio_30d")
                    ),
                    None,
                ),
                **(representative or {}),
                **{f"scenario_{k}": v for k, v in scenario_states.items()},
            }
        )

    # Canonical mutually exclusive state tally must account for the entire 307.
    state_counts = Counter(row["primary_status"] for row in company_records)
    if sum(state_counts.values()) != 307:
        raise RuntimeError("PRIMARY_STATUS_SUM_MISMATCH")
    user_eligible = [r for r in company_records if r["user_policy_status"] == "PASS"]
    user_complete = sum(r["data_status"] == "COMPLETE" for r in user_eligible)
    scenarios = scenario_summary(
        [
            i
            for i in raw
            if next(r for r in company_records if r["cvm_code"] == i["cvm_code"])[
                "user_policy_status"
            ]
            == "PASS"
        ],
        metrics_by_security,
        data_complete,
    )

    cap_population = [r for r in company_records if r["user_policy_status"] == "PASS"]
    cap_values = [Decimal(r["market_cap"]) for r in cap_population if r["market_cap"] is not None]
    cap_known = [r for r in cap_population if r["market_cap"] is not None]
    cap_quantiles = quantile_summary(
        [{"value": Decimal(r["market_cap"])} for r in cap_known], "value"
    )
    cap_thresholds = {
        **ABSOLUTE_CAP_THRESHOLDS,
        **{f"P{p}": percentile(cap_values, Decimal(p) / 100) for p in (25, 50, 75)},
    }
    cap_scenarios = {}
    for name, threshold in cap_thresholds.items():
        pass_rows = [r for r in cap_known if Decimal(r["market_cap"]) >= threshold]
        fail_rows = [r for r in cap_known if Decimal(r["market_cap"]) < threshold]
        review_count = len(cap_population) - len(cap_known)
        complete = sum(r["data_status"] == "COMPLETE" for r in pass_rows)
        cap_scenarios[name] = {
            "threshold_brl": str(threshold),
            "companies_pass": len(pass_rows),
            "companies_fail_in_scenario_only": len(fail_rows),
            "market_cap_unknown_review": review_count,
            "complete_pass": complete,
            "blocked_pass": len(pass_rows) - complete,
            "coverage_pass": pct(complete, len(pass_rows)),
            "coverage_retaining_unknown": pct(complete, len(pass_rows) + review_count),
        }

    blockers = []
    by_cvm = {r["cvm_code"]: r for r in company_records}
    for case in v5["cases"]:
        cvm = case["cvm_code"]
        blockers.append(
            {
                "blocker_type": "SOURCE_GAP",
                "cvm_code": cvm,
                "company": case["company"],
                "securities": [case["ticker"]],
                "source_status": case["terminal_status"],
            }
        )
    for case in v4_summary["unavailable_details"]:
        if case["cause"] == "SECURITY_TYPE_NOT_COVERED":
            blockers.append(
                {
                    "blocker_type": "SECURITY_TYPE_NOT_COVERED",
                    "cvm_code": case["cvm"],
                    "company": case["company"],
                    "securities": [s["ticker"] for s in case["securities"]],
                    "source_status": case["cause"],
                }
            )
    for case in v4_summary["no_trade_details"]:
        blockers.append(
            {
                "blocker_type": "NO_TRADE_ON_REFERENCE_DATE",
                "cvm_code": case["cvm"],
                "company": case["company"],
                "securities": [s["ticker"] for s in case["securities"]],
                "source_status": case["status"],
            }
        )
    for cvm, company in UNRESOLVED_NAMES.items():
        blockers.append(
            {
                "blocker_type": "UNRESOLVED",
                "cvm_code": cvm,
                "company": company,
                "securities": [],
                "source_status": "IDENTITY_UNRESOLVED",
            }
        )
    cross_blockers = []
    for blocker in blockers:
        cvm = str(blocker["cvm_code"]).zfill(6)
        issuer = by_cvm.get(cvm)
        if issuer:
            blocker.update(
                {
                    "found_in_v6_universe": True,
                    "structural_status": issuer["structural_status"],
                    "user_policy_status": issuer["user_policy_status"],
                    "primary_status": issuer["primary_status"],
                    "data_status": issuer["data_status"],
                    **{f"scenario_{k}": issuer[f"scenario_{k}"] for k in scenarios},
                }
            )
        else:
            blocker.update(
                {
                    "found_in_v6_universe": False,
                    "structural_status": "OUTSIDE_V6_BASELINE",
                    "user_policy_status": "REVIEW",
                    "primary_status": "IDENTITY_UNRESOLVED",
                    "data_status": "BLOCKED",
                    **{f"scenario_{k}": "REVIEW" for k in scenarios},
                }
            )
        cross_blockers.append(blocker)
    if len(cross_blockers) != 31:
        raise RuntimeError(f"BLOCKER_TOTAL_MISMATCH:{len(cross_blockers)}")

    # Utilities remain inside the methodology universe. The CVM taxonomy groups
    # sanitation, water and gas, so gas cannot safely be split by sector alone.
    utilities = []
    for row in company_records:
        sector = row["base_sector"] or ""
        if sector == "Energia Elétrica":
            kind = "ELECTRIC_UTILITY"
        elif sector == "Saneamento, Serv. Água e Gás":
            name = row["company"].upper()
            kind = (
                "GAS_NAMED_IN_COMPANY"
                if any(x in name for x in ("GÁS", "GAS", "COMGAS"))
                else "WATER_SANITATION_GAS_MIXED_CLASSIFICATION"
            )
        elif sector == "Telecomunicações":
            kind = "OTHER_REGULATED_ADJACENT_TELECOM"
        else:
            continue
        utilities.append(
            {
                "cvm_code": row["cvm_code"],
                "company": row["company"],
                "sector": row["sector"],
                "utility_classification": kind,
                "methodology_status": row["structural_status"],
            }
        )

    retail_exclusions = [
        r for r in company_records if r["user_policy_rule"] == "RETAIL_SECTOR_EXCLUSION"
    ]
    aviation_exclusions = [
        r for r in company_records if r["user_policy_rule"] == "AVIATION_COMPANY_EXCLUSION"
    ]
    unresolved_status_count = sum(
        r["primary_status"] == "IDENTITY_UNRESOLVED" for r in company_records
    )
    structural_all = [
        issuer
        for issuer in source_candidates
        if issuer.get("exclusion_reason") == "FINANCIAL_SECTOR"
    ]
    structural_rows = [
        {
            "cvm_code": str(i.get("cvm_code") or "").zfill(6),
            "cnpj": i.get("cnpj"),
            "company": i["display_name"],
            "sector": i.get("economic_sector"),
            "exclusion_rule": i.get("exclusion_reason"),
            "reason": (
                "Existing core exclusion: the current EY/ROC model is not "
                "comparable for financial issuers"
            ),
        }
        for i in structural_all
    ]
    result = {
        "audit": "MAGIC_FORMULA_INVESTABLE_UNIVERSE_AND_LIQUIDITY_V6",
        "mode": "AUDIT_ONLY_NO_RANKING",
        "reference_date": REFERENCE_DATE,
        "price_reference_date": PRICE_DATE,
        "snapshot_id": snapshot_id,
        "snapshot_created_at": created_at,
        "policy_version": POLICY.policy_version,
        "policy_activated": False,
        "raw_universe": {
            "v5_baseline_companies": len(raw),
            "raw_complete": sum(i["data_readiness_status"] == "FULL_DATA_READY" for i in raw),
            "raw_coverage": pct(
                sum(i["data_readiness_status"] == "FULL_DATA_READY" for i in raw), len(raw)
            ),
            "source_candidate_records": len(source_candidates),
            "existing_structural_financial_exclusions": len(structural_rows),
            "outside_v6_base_sector_or_identity_review": sum(
                i["methodology_eligibility"] == "REVIEW_REQUIRED" for i in source_candidates
            ),
        },
        "current_eligibility_rules": {
            "core_financial_exclusions": sorted(POLICY.structural_financial_sectors),
            "core_implementation": (
                "src/income_analytics/application/magic_formula_universe.py:classify_candidates"
            ),
            "core_status": "EXISTING_AND_UNCHANGED",
            "user_retail_rule": sorted(POLICY.user_retail_sectors),
            "user_aviation_cvm_codes": sorted(POLICY.user_aviation_cvm_codes),
            "user_policy_status": "AUDIT_CONFIGURATION_ONLY_NOT_ACTIVATED_IN_PRODUCTION",
            "minimum_market_cap_rule": "NONE_FOUND_IN_UNIVERSE_POLICY",
            "liquidity_rule": "NONE_FOUND; scenarios only",
            "market_type": "010 for reference prices; 020 is never a substitute",
        },
        "listing_counts": dict(Counter(r["listing_status"] for r in company_records)),
        "primary_status_counts": dict(sorted(state_counts.items())),
        "structural_eligible": len(raw),
        "structural_ineligible_within_v6_baseline": 0,
        "structural_coverage": pct(
            sum(r["data_status"] == "COMPLETE" for r in company_records), len(raw)
        ),
        "user_policy": {
            "eligible": len(user_eligible),
            "retail_excluded": len(retail_exclusions),
            "aviation_excluded": len(aviation_exclusions),
            "other_user_excluded": 0,
            "exceptions": [r for r in company_records if r["user_policy_exception"]],
            "complete": user_complete,
            "blocked": len(user_eligible) - user_complete,
            "coverage": pct(user_complete, len(user_eligible)),
            "retail_exclusion_cvm_codes": [r["cvm_code"] for r in retail_exclusions],
            "aviation_exclusion_cvm_codes": [r["cvm_code"] for r in aviation_exclusions],
        },
        "securities": {
            "security_rows": len(security_records),
            "companies_with_multiple_securities": sum(len(i["securities"]) > 1 for i in raw),
            "companies_with_multiple_share_classes": sum(
                len({s.get("share_class") for s in i["securities"]}) > 1 for i in raw
            ),
            "units_present": sum(
                any(s.get("share_class") == "UNIT" for s in i["securities"]) for i in raw
            ),
            "market_cap_issuer_level_consolidation": (
                "sum issued-minus-treasury ON/PN class capital times the same-class "
                "reference price; requires every positive class; counts each issuer once"
            ),
        },
        "liquidity": {
            "source_years": list(years),
            "session_count_2025_through_reference": len(sessions),
            "sessions_last30": sessions[-30:],
            "volume_field": (
                "COTAHIST VOLTOT positions 171-188, scaled by 100 to BRL; "
                "daily total by ticker+ISIN, market 010"
            ),
            "median_includes_zero_trading_sessions": True,
            "company_rule_for_scenarios": (
                "at least one identified share class passes; class volumes are "
                "not summed; class-selection policy remains undecided"
            ),
            "distributions": {
                field: quantile_summary(security_records, field)
                for field in (
                    "traded_days_ratio_30d",
                    "traded_days_ratio_90d",
                    "median_daily_financial_volume_30d",
                    "median_daily_financial_volume_90d",
                    "calendar_days_since_last_trade",
                )
            },
            "scenarios": scenarios,
        },
        "market_cap": {
            "available_companies": len(cap_known),
            "eligible_population": len(cap_population),
            "unknown_companies_review": len(cap_population) - len(cap_known),
            "distribution_brl": cap_quantiles,
            "scenarios": cap_scenarios,
            "minimum_market_cap_policy_changed": False,
        },
        "blockers": {
            "counts": dict(Counter(b["blocker_type"] for b in cross_blockers)),
            "source_gap": 14,
            "security_type_not_covered": 3,
            "no_trade": 9,
            "unresolved": 5,
            "rows": cross_blockers,
            "unresolved_silently_excluded": 0,
        },
        "utilities": {
            "rows": utilities,
            "counts": dict(Counter(u["utility_classification"] for u in utilities)),
            "policy": (
                "no new utility exclusion; electric and mixed water/sanitation/gas "
                "labels remain in existing core universe"
            ),
        },
        "source_manifests": manifests,
        **publication_guard(),
        "methodology_changed": False,
        "company_rows": company_records,
        "security_rows": security_records,
        "structural_exclusion_rows": structural_rows,
    }
    if result["raw_universe"]["raw_complete"] != 185:
        raise RuntimeError("RAW_COMPLETE_BASELINE_CHANGED")
    if result["user_policy"]["exceptions"][0]["cvm_code"] != "025372":
        raise RuntimeError("ASAI3_EXCEPTION_NOT_AUDITABLE")
    if len(blockers) != 31 or unresolved_status_count > 5:
        raise RuntimeError("BLOCKER_OR_UNRESOLVED_INVARIANT_FAILED")
    (ROOT / "v6-audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    write_csv(ROOT / "v6-company-eligibility.csv", company_records)
    write_csv(ROOT / "v6-security-liquidity.csv", security_records)
    write_csv(ROOT / "v6-structural-exclusions.csv", structural_rows)
    write_csv(ROOT / "v6-current-blockers.csv", cross_blockers)
    print(
        json.dumps(
            {
                "audit": result["audit"],
                "raw": result["raw_universe"],
                "user_policy": {
                    k: v
                    for k, v in result["user_policy"].items()
                    if k
                    not in (
                        "exceptions",
                        "retail_exclusion_cvm_codes",
                        "aviation_exclusion_cvm_codes",
                    )
                },
                "status_counts": result["primary_status_counts"],
                "liquidity_scenarios": {
                    k: {kk: vv for kk, vv in v.items() if kk != "states_by_cvm"}
                    for k, v in scenarios.items()
                },
                "market_cap_available": result["market_cap"]["available_companies"],
                "blockers": result["blockers"]["counts"],
                "archive_manifests": manifests,
            },
            ensure_ascii=False,
            default=str,
        )
    )
    return result


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    run()
