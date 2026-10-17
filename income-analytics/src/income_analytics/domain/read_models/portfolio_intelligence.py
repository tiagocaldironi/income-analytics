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
    trajectory_tolerance: Decimal = Decimal("0.01")
    surface_tolerance: Decimal = Decimal("0.001")


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioFinding:
    code: str
    category: str
    severity: str
    title: str
    description: str
    evidence: dict[str, Decimal | str]
    as_of: date | None
    logical_key: str = ""
    subject: dict[str, str] | None = None
    reference: dict[str, object] | None = None
    current_value: Decimal | None = None
    comparison_value: Decimal | None = None
    change: Decimal | None = None
    change_pp: Decimal | None = None
    comparison_as_of: date | None = None
    decomposition: tuple[dict[str, object], ...] = ()
    trajectory: str = "UNKNOWN"
    materiality: str = "LOW"
    materiality_reasons: tuple[str, ...] = ()
    should_surface: bool = True
    structured_evidence: tuple[dict[str, Decimal | str | date | None], ...] = ()
    causes: tuple[dict[str, Decimal | str], ...] = ()
    data_quality: dict[str, object] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioIntelligence:
    as_of: date | None
    findings: tuple[PortfolioFinding, ...]
    info_count: int
    attention_count: int
    high_attention_count: int
