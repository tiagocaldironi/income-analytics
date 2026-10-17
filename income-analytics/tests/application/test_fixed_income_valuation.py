from datetime import date
from decimal import Decimal
from uuid import uuid4

from income_analytics.application.fixed_income_valuation import FixedIncomeValuationEngine
from income_analytics.domain.benchmark_rate import BenchmarkRate
from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)
from income_analytics.domain.fixed_income_details import FixedIncomeDetails


def test_prefixed_curve_uses_explicit_act_365f() -> None:
    details = FixedIncomeDetails(
        asset_id=uuid4(),
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.PREFIXED,
        application_date=date(2025, 1, 1),
        principal_amount=Decimal("1000"),
        contracted_rate=Decimal("10"),
    )

    value = FixedIncomeValuationEngine.value(details, as_of=date(2026, 1, 1))

    assert value.gross_value == Decimal("1100.0")


def test_cdi_percent_requires_observations_instead_of_fabricating_value() -> None:
    details = FixedIncomeDetails(
        asset_id=uuid4(),
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.CDI_PERCENT,
        application_date=date(2026, 1, 1),
        principal_amount=Decimal("1000"),
        percentage_of_indexer=Decimal("110"),
    )

    unavailable = FixedIncomeValuationEngine.value(details, as_of=date(2026, 1, 2))
    value = FixedIncomeValuationEngine.value(
        details,
        as_of=date(2026, 1, 2),
        cdi_rates=(
            BenchmarkRate(
                name="CDI", effective_date=date(2026, 1, 2), return_percentage=Decimal("0.01")
            ),
        ),
    )

    assert unavailable.gross_value is None
    assert value.gross_value == Decimal("1000") * Decimal("1.011")


def test_cdi_contract_is_valued_at_principal_on_application_date() -> None:
    details = FixedIncomeDetails(
        asset_id=uuid4(),
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.CDI_PERCENT,
        application_date=date(2026, 1, 1),
        principal_amount=Decimal("1000"),
        percentage_of_indexer=Decimal("120"),
    )

    value = FixedIncomeValuationEngine.value(details, as_of=date(2026, 1, 1))

    assert value.gross_value == Decimal("1000")


def test_savings_credits_on_monthly_anniversary_with_official_inputs() -> None:
    details = FixedIncomeDetails(
        asset_id=uuid4(),
        instrument_type=FixedIncomeInstrumentType.SAVINGS_ACCOUNT,
        indexer_type=FixedIncomeIndexerType.SAVINGS_RULE,
        application_date=date(2026, 1, 15),
        principal_amount=Decimal("1000"),
    )

    value = FixedIncomeValuationEngine.value(
        details,
        as_of=date(2026, 2, 15),
        tr_rates=((date(2026, 2, 15), Decimal("0")),),
        selic_targets=((date(2026, 2, 15), Decimal("0.10")),),
    )

    assert value.gross_value == Decimal("1005.000")


def test_ipca_plus_keeps_principal_when_no_new_monthly_index_exists_yet() -> None:
    details = FixedIncomeDetails(
        asset_id=uuid4(),
        instrument_type=FixedIncomeInstrumentType.TESOURO_DIRETO,
        indexer_type=FixedIncomeIndexerType.IPCA_PLUS,
        application_date=date(2026, 8, 28),
        principal_amount=Decimal("1000"),
        spread=Decimal("5"),
    )

    value = FixedIncomeValuationEngine.value(
        details,
        as_of=date(2026, 8, 28),
        ipca_rates=((date(2026, 7, 1), Decimal("0.0007")),),
    )

    assert value.gross_value == Decimal("1000")


def test_cdi_plus_applies_the_contracted_cdi_percentage_before_spread() -> None:
    details = FixedIncomeDetails(
        asset_id=uuid4(),
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.CDI_PLUS,
        application_date=date(2026, 1, 1),
        principal_amount=Decimal("1000"),
        percentage_of_indexer=Decimal("120"),
        spread=Decimal("2"),
    )

    value = FixedIncomeValuationEngine.value(
        details,
        as_of=date(2026, 1, 2),
        cdi_rates=(
            BenchmarkRate(
                name="CDI", effective_date=date(2026, 1, 2), return_percentage=Decimal("0.01")
            ),
        ),
    )

    assert value.gross_value is not None
    assert value.gross_value > Decimal("1012")
