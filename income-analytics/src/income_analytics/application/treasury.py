"""Treasury presentation and trade-boundary rules; never rewrite historical units.

Traditional Tesouro Direto orders use multiples of 0.01 title. Contract-valued
legacy applications use a different unit and cannot be converted implicitly.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from income_analytics.application.holdings_display import TreasuryPresentation
from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.enums.fixed_income import FixedIncomeInstrumentType
from income_analytics.domain.fixed_income_details import FixedIncomeDetails

STEP = Decimal("0.01")


def validate_title_history(events: Iterable[FinancialEvent], asset_id: UUID) -> None:
    """Reject uncovered sales before the tolerant historical projector sees them."""
    balance = Decimal("0")
    for event in sorted(events, key=lambda item: (item.effective_date, item.registered_at)):
        if event.asset is None or event.asset.id != asset_id or event.quantity is None:
            continue
        if event.event_type is FinancialEventType.BUY:
            balance += event.quantity.value
        elif event.event_type is FinancialEventType.SELL:
            balance -= event.quantity.value
            if balance < 0:
                raise ValueError("Quantidade de títulos insuficiente na data da venda.")


def title_name(name: str) -> str | None:
    """Recognize explicit traditional names/codes, including coupon variants."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().upper()
    text = re.sub(r"\s+", " ", text).strip()
    year = re.search(r"\b(20\d{2}|21\d{2})\b", text)
    if not year:
        return None
    if re.match(r"^(TESOURO SELIC|LFT)\b", text):
        label = "Tesouro Selic"
    elif re.match(r"^(TESOURO IPCA|NTN[- ]?B)\b", text):
        label = "Tesouro IPCA+"
        if "JUROS" in text or re.match(r"^NTN[- ]?B\b", text) and "PRINC" not in text:
            label += " com Juros Semestrais"
    elif re.match(r"^(TESOURO PREFIXADO|LTN|NTN[- ]?F)\b", text):
        label = "Tesouro Prefixado"
        if "JUROS" in text or re.match(r"^NTN[- ]?F\b", text):
            label += " com Juros Semestrais"
    elif re.match(r"^TESOURO RENDA\b", text):
        label = "Tesouro RendA+"
    elif re.match(r"^TESOURO EDUCA\b", text):
        label = "Tesouro Educa+"
    else:
        return None
    return f"{label} {year.group(0)}"


def tradable_title(name: str) -> bool:
    label = title_name(name)
    return label is not None and label.startswith(
        ("Tesouro Selic ", "Tesouro IPCA+ ", "Tesouro Prefixado ")
    )


def is_treasury(asset: Asset, details: FixedIncomeDetails | None = None) -> bool:
    if asset.asset_class is not AssetClass.FIXED_INCOME:
        return False
    if details is not None:
        return details.instrument_type is FixedIncomeInstrumentType.TESOURO_DIRETO
    if getattr(asset, "asset_type", None) in {AssetType.CDB, AssetType.LCI, AssetType.LCA}:
        return False
    return (
        getattr(asset, "asset_type", None) is AssetType.TREASURY
        or title_name(asset.name) is not None
    )


def presentation(asset: Asset, details: FixedIncomeDetails | None) -> TreasuryPresentation:
    if not is_treasury(asset, details):
        if asset.asset_class is AssetClass.FIXED_INCOME:
            bank = (
                getattr(asset, "asset_type", None) in {AssetType.CDB, AssetType.LCI, AssetType.LCA}
                or details is not None
                and details.instrument_type
                in {
                    FixedIncomeInstrumentType.CDB,
                    FixedIncomeInstrumentType.RDB,
                    FixedIncomeInstrumentType.LCI,
                    FixedIncomeInstrumentType.LCA,
                    FixedIncomeInstrumentType.SAVINGS_ACCOUNT,
                }
            )
            return {"display_group": "FIXED_INCOME" if bank else "OTHER_FIXED_INCOME"}
        return {}
    return {
        "display_group": "TREASURY",
        "display_name": title_name(asset.name) or "Tesouro Direto — identificação pendente",
        "quantity_unit": "LEGACY_CONTRACT" if details is not None else "TITLE",
        "treasury_trade_supported": details is None and tradable_title(asset.name),
    }


def validate_trade(quantity: Decimal, price: Decimal, gross_amount: Decimal | None = None) -> None:
    if not quantity.is_finite() or quantity <= 0 or quantity % STEP:
        raise ValueError("Tesouro Direto exige quantidade positiva em múltiplos de 0,01 título.")
    if not price.is_finite() or price <= 0:
        raise ValueError("Informe o preço unitário positivo do título.")
    if gross_amount is not None:
        expected = (quantity * price).quantize(STEP, rounding=ROUND_HALF_UP)
        if not gross_amount.is_finite() or gross_amount != expected:
            raise ValueError(
                (
                    "Valor bruto divergente de quantidade × preço unitário; "
                    "informe custos separadamente."
                )
            )
