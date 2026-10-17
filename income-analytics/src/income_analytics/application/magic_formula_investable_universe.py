"""Declarative, audit-only policy and liquidity analysis for Magic Formula."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import median
from typing import Iterable


@dataclass(frozen=True, slots=True)
class MagicFormulaUniversePolicy:
    """Legacy V6 audit configuration; V8 screening lives in magic_formula_screening."""

    policy_version: str = "MF_BR_2027_V1_DRAFT"
    structural_financial_sectors: frozenset[str] = frozenset(
        {
            "Bancos",
            "Seguradoras e Corretoras",
            "Intermediação Financeira",
            "Crédito Imobiliário",
            "Arrendamento Mercantil",
            "Securitização de Recebíveis",
        }
    )
    user_retail_sectors: frozenset[str] = frozenset({"Comércio (Atacado e Varejo)"})
    user_aviation_cvm_codes: frozenset[str] = frozenset({"024112", "019569"})
    ticker_exceptions: tuple[tuple[str, str, str], ...] = (
        ("ASAI3", "025372", "ALLOW_RETAIL_EXCLUSION_EXCEPTION"),
    )
    commerce_policy_excluded_categories: frozenset[str] = frozenset({"TRADITIONAL_RETAIL"})
    commerce_policy_review_categories: frozenset[str] = frozenset({"MIXED_COMMERCE", "UNCERTAIN"})
    security_selection_policy: str = "S4"
    security_selection_primary_metric: str = "traded_days_ratio_30d"
    security_selection_tie_breaker: str = "median_daily_financial_volume_30d"
    security_selection_final_tie_breaker: str = "stable_security_identity_key"
    liquidity_policy_metric: str = "traded_days_ratio_30d"
    liquidity_policy_minimum: Decimal = Decimal("0.50")
    liquidity_policy_activated: bool = False
    security_selection_policy_activated: bool = False
    minimum_market_cap_policy_enabled: bool = False
    minimum_market_cap_policy_brl: Decimal | None = None


POLICY = MagicFormulaUniversePolicy()


def normalized_sector(sector: str | None) -> str | None:
    if not sector:
        return None
    return sector.removeprefix("Emp. Adm. Part. - ").strip()


def structural_decision(issuer: dict, policy: MagicFormulaUniversePolicy = POLICY) -> dict:
    sector = normalized_sector(issuer.get("economic_sector"))
    excluded = sector in policy.structural_financial_sectors
    return {
        "status": "INELIGIBLE_STRUCTURAL" if excluded else "PASS",
        "rule": "FINANCIAL_SECTOR" if excluded else None,
        "sector": sector,
        "reason": "EY/ROC accounting model is not comparable for financial issuers"
        if excluded
        else None,
    }


def legacy_user_policy_decision(issuer: dict, policy: MagicFormulaUniversePolicy = POLICY) -> dict:
    """Reproduce historical V6 decisions for audit artifacts only."""
    sector = normalized_sector(issuer.get("economic_sector"))
    tickers = {str(s.get("ticker") or "").upper() for s in issuer.get("securities", [])}
    cvm = str(issuer.get("cvm_code") or "").zfill(6)
    for ticker, exception_cvm, effect in policy.ticker_exceptions:
        if ticker in tickers and cvm == exception_cvm:
            return {
                "status": "PASS",
                "rule": "TICKER_EXCEPTION",
                "exception": effect,
                "reason": f"{ticker} explicitly overrides the retail sector exclusion",
            }
    if sector in policy.user_retail_sectors:
        return {
            "status": "INELIGIBLE_USER_POLICY",
            "rule": "RETAIL_SECTOR_EXCLUSION",
            "exception": None,
            "reason": "CVM sector taxonomy is Comércio (Atacado e Varejo)",
        }
    if cvm in policy.user_aviation_cvm_codes:
        return {
            "status": "INELIGIBLE_USER_POLICY",
            "rule": "AVIATION_COMPANY_EXCLUSION",
            "exception": None,
            "reason": "explicit user policy excludes airline issuers",
        }
    return {"status": "PASS", "rule": None, "exception": None, "reason": None}


def user_policy_decision(issuer: dict, policy: MagicFormulaUniversePolicy = POLICY) -> dict:
    """V8 canonical eligibility ignores retail and aviation screening preferences.

    The ``policy`` argument remains for source compatibility with callers from
    V6/V7. Use ``legacy_user_policy_decision`` only when reproducing old audits.
    """
    del policy
    return {
        "status": "PASS",
        "rule": None,
        "exception": None,
        "reason": None,
        "screening_required": True,
    }


def listing_status(securities: Iterable[dict], reference_date: str) -> str:
    """Assess whether at least one identified class was listed on the reference date."""
    ref = date.fromisoformat(reference_date)
    statuses = []
    for security in securities:
        start_raw, end_raw = security.get("valid_from"), security.get("valid_to")
        try:
            start = date.fromisoformat(start_raw) if start_raw else None
            end = date.fromisoformat(end_raw) if end_raw else None
        except TypeError:
            statuses.append("UNCERTAIN")
            continue
        except ValueError:
            statuses.append("UNCERTAIN")
            continue
        if start and start > ref:
            statuses.append("NOT_LISTED_YET")
        elif end and end < ref:
            statuses.append("DELISTED_BEFORE_REFERENCE_DATE")
        elif start or security.get("effective_market_date") == ref.isoformat():
            statuses.append("LISTED_ON_REFERENCE_DATE")
        else:
            statuses.append("UNCERTAIN")
    if "LISTED_ON_REFERENCE_DATE" in statuses:
        return "LISTED_ON_REFERENCE_DATE"
    if statuses and all(s == "NOT_LISTED_YET" for s in statuses):
        return "NOT_LISTED_YET"
    if statuses and all(s == "DELISTED_BEFORE_REFERENCE_DATE" for s in statuses):
        return "DELISTED_BEFORE_REFERENCE"
    return "UNCERTAIN"


def security_liquidity_metrics(
    trading_sessions: list[str],
    trade_volume_by_date: dict[str, Decimal],
    reference_date: str,
) -> dict:
    """Calculate trading and zero-inclusive volume metrics over trailing sessions."""
    sessions = [d for d in trading_sessions if d <= reference_date]
    last_trade = max(trade_volume_by_date, default=None)
    result = {"last_trade_date": last_trade}
    for window in (30, 60, 90):
        days = sessions[-window:]
        traded_days = sum(d in trade_volume_by_date for d in days)
        volumes = [trade_volume_by_date.get(d, Decimal(0)) for d in days]
        result[f"trading_days_{window}d"] = len(days)
        result[f"days_with_trade_{window}d"] = traded_days
        result[f"traded_days_ratio_{window}d"] = (
            Decimal(traded_days) / Decimal(len(days)) if days else None
        )
        result[f"median_daily_financial_volume_{window}d"] = (
            Decimal(str(median(volumes))) if volumes else None
        )
    if last_trade:
        result["calendar_days_since_last_trade"] = (
            date.fromisoformat(reference_date) - date.fromisoformat(last_trade)
        ).days
        result["trading_days_since_last_trade"] = sum(d > last_trade for d in sessions)
    else:
        result["calendar_days_since_last_trade"] = None
        result["trading_days_since_last_trade"] = None
    return result


def liquidity_scenario(metrics: dict | None, scenario: str) -> str:
    """Return PASS/FAIL/REVIEW; missing liquidity evidence is never an exclusion."""
    if scenario == "L0":
        return "PASS"
    if not metrics:
        return "REVIEW"
    gap = metrics.get("calendar_days_since_last_trade")
    ratio = metrics.get("traded_days_ratio_30d")
    volume = metrics.get("median_daily_financial_volume_30d")
    condition = {
        "L1": None if gap is None else gap <= 7,
        "L2": None if gap is None else gap <= 30,
        "L3": None if ratio is None else ratio >= Decimal("0.50"),
        "L4": None if ratio is None else ratio >= Decimal("0.80"),
        "L5": None if volume is None else volume >= Decimal("100000"),
        "L6": None if volume is None else volume >= Decimal("500000"),
    }
    no_trade_in_checked_window = metrics.get("metric_status") == ("OBSERVED_NO_010_TRADE_2019_2025")
    if scenario in {"L1", "L2"} and gap is None and no_trade_in_checked_window:
        return "FAIL"
    if scenario == "L7":
        conditions = (
            False
            if gap is None and no_trade_in_checked_window
            else (None if gap is None else gap <= 30),
            None if ratio is None else ratio >= Decimal("0.50"),
            None if volume is None else volume >= Decimal("100000"),
        )
        if False in conditions:
            return "FAIL"
        return "REVIEW" if None in conditions else "PASS"
    if scenario not in condition:
        raise ValueError(f"UNKNOWN_LIQUIDITY_SCENARIO:{scenario}")
    if condition[scenario] is None:
        return "REVIEW"
    return "PASS" if condition[scenario] else "FAIL"


def primary_status(
    *,
    structural: dict,
    user_policy: dict,
    data_complete: bool,
    liquidity_metrics: dict | None,
    identity_unresolved: bool = False,
) -> str:
    """One auditable state per baseline company; liquidity remains review-only."""
    if identity_unresolved:
        return "IDENTITY_UNRESOLVED"
    if structural["status"] == "INELIGIBLE_STRUCTURAL":
        return "INELIGIBLE_STRUCTURAL"
    if user_policy["status"] == "INELIGIBLE_USER_POLICY":
        return "INELIGIBLE_USER_POLICY"
    if (
        liquidity_metrics is None
        or liquidity_metrics.get("traded_days_ratio_30d") is None
        or liquidity_metrics["traded_days_ratio_30d"] < Decimal("0.50")
    ):
        return "LIQUIDITY_REVIEW"
    return "ELIGIBLE_COMPLETE" if data_complete else "ELIGIBLE_DATA_BLOCKED"


def market_type_is_eligible(market_type: str) -> bool:
    """V6 preserves 010 spot prices; fractional 020 is never an automatic fallback."""
    return market_type == "010"


def aggregate_daily_financial_volume(records: Iterable[dict]) -> dict[str, Decimal]:
    """Sum VOLTOT only within one already-identified security and session."""
    totals: dict[str, Decimal] = {}
    for record in records:
        day = str(record["date"])
        value = Decimal(str(record["volume"]))
        if value < 0:
            raise ValueError("NEGATIVE_FINANCIAL_VOLUME")
        totals[day] = totals.get(day, Decimal(0)) + value
    return totals


def coverage_by_eligibility(companies: Iterable[dict]) -> dict:
    """Data gaps remain in the denominator; only structural/user policy can remove."""
    eligible = [
        item
        for item in companies
        if item.get("structural_status") == "PASS" and item.get("user_policy_status") == "PASS"
    ]
    complete = sum(bool(item.get("data_complete")) for item in eligible)
    return {
        "complete": complete,
        "eligible_denominator": len(eligible),
        "blocked": len(eligible) - complete,
        "coverage": Decimal(100) * complete / len(eligible) if eligible else Decimal(0),
    }


def publication_guard() -> dict:
    """V6 never computes or publishes a rank, regardless of coverage/scenario."""
    return {
        "ranking_calculated": False,
        "ranking_active": False,
        "ranking_blocked": True,
        "top_30_published": False,
    }


def company_liquidity_scenario(security_metrics: Iterable[dict | None], scenario: str) -> str:
    """A company passes when one separately measured class can be invested.

    This does not sum liquidity across share classes and an unknown class keeps
    the company in review unless another identified class passes.
    """
    if scenario == "L0":
        return "PASS"
    states = [liquidity_scenario(metrics, scenario) for metrics in security_metrics]
    if "PASS" in states:
        return "PASS"
    if not states or "REVIEW" in states:
        return "REVIEW"
    return "FAIL"
