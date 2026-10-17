from decimal import Decimal

from income_analytics.application.monetary_amount import (
    CurrencyScale,
    MonetaryScaleNormalizer,
)


def test_brl_unit_stays_equal_with_lineage() -> None:
    amount = MonetaryScaleNormalizer().normalize(
        raw_value=Decimal("12.34"), currency="BRL", scale=CurrencyScale.UNIT, source="fixture"
    )
    assert amount.normalized_value == Decimal("12.34")
    assert amount.normalization_multiplier == Decimal("1")
    assert amount.normalization_rule_id == "MONETARY_SCALE_BRL_UNIT_V1"


def test_brl_thousand_and_million_use_decimal_multipliers() -> None:
    normalizer = MonetaryScaleNormalizer()
    thousand = normalizer.normalize(
        raw_value=Decimal("51"), currency="BRL", scale=CurrencyScale.THOUSAND, source="fixture"
    )
    million = normalizer.normalize(
        raw_value=Decimal("2"), currency="BRL", scale=CurrencyScale.MILLION, source="fixture"
    )
    assert thousand.normalized_value == Decimal("51000")
    assert million.normalized_value == Decimal("2000000")


def test_unknown_scale_does_not_normalize() -> None:
    amount = MonetaryScaleNormalizer().normalize(
        raw_value=Decimal("1"), currency="BRL", scale=CurrencyScale.UNKNOWN, source="fixture"
    )
    assert amount.normalized_value is None
    assert amount.normalization_multiplier is None
