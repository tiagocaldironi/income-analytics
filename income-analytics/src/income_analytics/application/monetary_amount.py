"""Explicit monetary-scale normalization for auditable financial calculations."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class CurrencyScale(StrEnum):
    UNIT = "UNIT"
    THOUSAND = "THOUSAND"
    MILLION = "MILLION"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class MonetaryAmount:
    raw_value: Decimal
    currency: str
    source_scale: CurrencyScale
    normalized_value: Decimal | None
    normalized_currency: str
    normalization_multiplier: Decimal | None
    normalization_rule_id: str | None
    source: str


class MonetaryScaleNormalizer:
    _multipliers = {
        CurrencyScale.UNIT: (Decimal("1"), "MONETARY_SCALE_BRL_UNIT_V1"),
        CurrencyScale.THOUSAND: (Decimal("1000"), "MONETARY_SCALE_BRL_THOUSAND_V1"),
        CurrencyScale.MILLION: (Decimal("1000000"), "MONETARY_SCALE_BRL_MILLION_V1"),
    }
    _cvm_scales = {
        "UNIDADE": CurrencyScale.UNIT,
        "MIL": CurrencyScale.THOUSAND,
        "MILHAO": CurrencyScale.MILLION,
        "MILHÃO": CurrencyScale.MILLION,
    }

    def from_cvm(
        self, *, raw_value: Decimal, currency: str, source_scale: str, source: str
    ) -> MonetaryAmount:
        scale = self._cvm_scales.get(source_scale.strip().upper(), CurrencyScale.UNKNOWN)
        return self.normalize(raw_value=raw_value, currency=currency, scale=scale, source=source)

    def normalize(
        self, *, raw_value: Decimal, currency: str, scale: CurrencyScale, source: str
    ) -> MonetaryAmount:
        if currency != "BRL" or scale not in self._multipliers:
            return MonetaryAmount(raw_value, currency, scale, None, "BRL", None, None, source)
        multiplier, rule_id = self._multipliers[scale]
        return MonetaryAmount(
            raw_value, currency, scale, raw_value * multiplier, "BRL", multiplier, rule_id, source
        )
