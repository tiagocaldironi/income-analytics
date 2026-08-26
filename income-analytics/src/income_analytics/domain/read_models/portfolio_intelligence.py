"""Structured, deterministic portfolio diagnostic outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class DiagnosticThresholds:
    max_asset_weight: Decimal = Decimal("0.25")
    max_class_weight: Decimal = Decimal("0.50")
    max_country_weight: Decimal = Decimal("0.70")
    max_sector_weight: Decimal = Decimal("0.45")
    max_portfolio_drift: Decimal = Decimal("0.10")
    max_risk_contribution_multiple: Decimal = Decimal("2")


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioFinding:
    code: str
    category: str
    severity: str
    title: str
    description: str
    evidence: dict[str, Decimal | str]
    as_of: date | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioIntelligence:
    as_of: date | None
    findings: tuple[PortfolioFinding, ...]
    info_count: int
    attention_count: int
    high_attention_count: int
