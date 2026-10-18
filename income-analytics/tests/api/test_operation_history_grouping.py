from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from income_analytics.api.routers import dashboard
from income_analytics.api.routers.dashboard import (
    _fixed_income_condition,
    _fixed_income_contract_key,
    _operation_group,
)
from income_analytics.application.base_currency_valuation import (
    BaseCurrencyPosition,
    BaseCurrencyValuation,
)
from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)
from income_analytics.domain.fixed_income_details import FixedIncomeDetails
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from tests.unit.domain.builders import build_asset


def make_event(
    event_type: FinancialEventType, *, asset_type: AssetType | None = None
) -> FinancialEvent:
    asset = (
        build_asset(asset_type=asset_type, asset_class=AssetClass.OTHER)
        if asset_type is not None
        else None
    )
    return FinancialEvent(
        account_id=uuid4(),
        asset=asset,
        event_type=event_type,
        occurred_at=datetime(2026, 8, 1, tzinfo=UTC),
        effective_date=datetime(2026, 8, 1, tzinfo=UTC).date(),
        quantity=(
            Quantity(Decimal("1")) if asset and event_type is FinancialEventType.BUY else None
        ),
        unit_price=(
            Money(Decimal("100")) if asset and event_type is FinancialEventType.BUY else None
        ),
        amount=Money(Decimal("100")) if event_type is not FinancialEventType.BUY else None,
    )


@pytest.mark.parametrize(
    ("event_type", "asset_type", "expected"),
    [
        (FinancialEventType.BUY, AssetType.STOCK, "OTHER"),
        (FinancialEventType.BUY, AssetType.PENSION, "PENSION"),
        (FinancialEventType.BUY, AssetType.REAL_ESTATE, "REAL_ESTATE"),
        (FinancialEventType.DIVIDEND, AssetType.STOCK, "INCOME"),
        (FinancialEventType.DEPOSIT, None, "CONTRIBUTIONS"),
        (FinancialEventType.WITHDRAWAL, None, "WITHDRAWALS"),
    ],
)
def test_history_grouping_uses_domain_event_and_asset_classification(
    event_type: FinancialEventType,
    asset_type: AssetType | None,
    expected: str,
) -> None:
    assert _operation_group(make_event(event_type, asset_type=asset_type))[0] == expected


def test_fixed_income_contract_key_includes_instrument_indexer_and_rate() -> None:
    asset = build_asset(name="Nubank", asset_type=AssetType.FIXED_INCOME)
    cdi_contract = FixedIncomeDetails(
        asset_id=asset.id,
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.CDI_PERCENT,
        application_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
        principal_amount=Decimal("1000"),
        percentage_of_indexer=Decimal("120"),
    )
    prefixed_contract = FixedIncomeDetails(
        asset_id=asset.id,
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.PREFIXED,
        application_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
        principal_amount=Decimal("1000"),
        contracted_rate=Decimal("12"),
    )

    assert _fixed_income_contract_key(asset, cdi_contract) != _fixed_income_contract_key(
        asset, prefixed_contract
    )
    assert _fixed_income_condition(cdi_contract) == "120% do CDI"


def test_fixed_income_condition_uses_a_product_label_for_ipca_spread() -> None:
    asset = build_asset(name="Tesouro IPCA", asset_type=AssetType.FIXED_INCOME)
    details = FixedIncomeDetails(
        asset_id=asset.id,
        instrument_type=FixedIncomeInstrumentType.TESOURO_DIRETO,
        indexer_type=FixedIncomeIndexerType.IPCA_PLUS,
        application_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
        principal_amount=Decimal("1000"),
        spread=Decimal("8"),
    )

    assert _fixed_income_condition(details) == "IPCA + 8%"


def test_fixed_income_condition_includes_percentage_and_spread_for_cdi_plus() -> None:
    asset = build_asset(name="Banco", asset_type=AssetType.FIXED_INCOME)
    details = FixedIncomeDetails(
        asset_id=asset.id,
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.CDI_PLUS,
        application_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
        principal_amount=Decimal("1000"),
        percentage_of_indexer=Decimal("120"),
        spread=Decimal("2"),
    )

    assert _fixed_income_condition(details) == "120% do CDI + 2%"


def test_holdings_class_aggregates_the_result_of_its_positions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    portfolio = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    portfolio.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        quantity=Decimal("100"),
        unit_price=Decimal("30"),
    )
    portfolio.update_market_price(ticker="PETR4", current_price=Decimal("40"))
    monkeypatch.setattr(dashboard, "session", portfolio)

    holdings = dashboard.get_portfolio_holdings()

    assert holdings["classes"][0]["total_result"] == Decimal("1000")


def test_holdings_class_converts_foreign_result_to_the_base_currency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    portfolio = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    portfolio.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="MCD",
        asset_class=AssetClass.INTERNATIONAL,
        country="US",
        currency_code="USD",
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
    )
    portfolio.update_market_price(ticker="MCD", current_price=Decimal("110"))
    valuation = BaseCurrencyValuation(
        base_currency="BRL",
        positions=(
            BaseCurrencyPosition(
                ticker="MCD",
                native_currency="USD",
                market_value_native=Decimal("110"),
                market_value_base=Decimal("550"),
                fx_rate=Decimal("5"),
                fx_effective_date=None,
            ),
        ),
        market_value=Decimal("550"),
        cash=None,
        equity=None,
        complete=True,
    )
    monkeypatch.setattr(dashboard, "session", portfolio)
    monkeypatch.setattr(
        PortfolioSession,
        "base_currency_valuation",
        lambda self, *, as_of=None: valuation,
    )

    holdings = dashboard.get_portfolio_holdings()

    assert holdings["classes"][0]["total_result"] == Decimal("50")


def test_operations_history_filters_income_and_movements_independently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    portfolio = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    portfolio.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("2"),
        unit_price=Decimal("30"),
        effective_date=datetime(2026, 9, 29, tzinfo=UTC).date(),
    )
    portfolio.register_dividend(
        ticker="PETR4",
        amount=Decimal("5"),
        effective_date=datetime(2026, 9, 25, tzinfo=UTC).date(),
    )
    monkeypatch.setattr(dashboard, "session", portfolio)

    movements = dashboard.get_operations_history(movement_type="MOVEMENTS")
    income = dashboard.get_operations_history(movement_type="INCOME")
    buys = dashboard.get_operations_history(movement_type="MOVEMENTS", event_type="BUY")
    stock_income = dashboard.get_operations_history(
        movement_type="INCOME", asset_class=AssetClass.BRAZILIAN_STOCK.value
    )

    assert [item["event_type"] for group in movements["groups"] for item in group["events"]] == [
        "BUY"
    ]
    assert [item["event_type"] for group in income["groups"] for item in group["events"]] == [
        "DIVIDEND"
    ]
    assert [item["event_type"] for group in buys["groups"] for item in group["events"]] == ["BUY"]
    assert [item["event_type"] for group in stock_income["groups"] for item in group["events"]] == [
        "DIVIDEND"
    ]
    assert any(
        item["key"] == AssetClass.BRAZILIAN_STOCK.value
        for item in stock_income["available_classes"]
    )


def test_operations_history_returns_independent_event_type_cursors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    portfolio = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    portfolio.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("1"),
        unit_price=Decimal("30"),
        effective_date=datetime(2026, 9, 29, tzinfo=UTC).date(),
    )
    portfolio.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="WEGE3",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("2"),
        unit_price=Decimal("50"),
        effective_date=datetime(2026, 9, 28, tzinfo=UTC).date(),
    )
    portfolio.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("100"),
        effective_date=datetime(2026, 9, 27, tzinfo=UTC).date(),
    )
    portfolio.register_external_flow(
        event_type=FinancialEventType.WITHDRAWAL,
        amount=Decimal("20"),
        effective_date=datetime(2026, 9, 26, tzinfo=UTC).date(),
    )
    monkeypatch.setattr(dashboard, "session", portfolio)

    grouped = dashboard.get_operations_history(
        group_by="TYPE", movement_type="MOVEMENTS", page_size=1
    )
    groups = {group["key"]: group for group in grouped["groups"]}
    buy_more = dashboard.get_operations_history(
        group_by="TYPE", movement_type="MOVEMENTS", group_key="BUY", offset=1, page_size=1
    )
    timeline_first = dashboard.get_operations_history(group_by="DATE", offset=0, page_size=2)
    timeline_next = dashboard.get_operations_history(group_by="DATE", offset=2, page_size=2)

    assert groups["BUY"]["total"] == 2
    assert groups["BUY"]["has_more"] is True
    assert groups["DEPOSIT"]["total"] == 1
    assert groups["WITHDRAWAL"]["total"] == 1
    assert [item["ticker"] for item in buy_more["groups"][0]["events"]] == ["WEGE3"]
    assert timeline_first["groups"][0]["has_more"] is True
    assert len(timeline_first["groups"][0]["events"]) == 2
    assert (
        timeline_next["groups"][0]["events"][0]["effective_date"]
        < timeline_first["groups"][0]["events"][-1]["effective_date"]
    )


def test_b3_import_history_exposes_persisted_batch_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from income_analytics.application.b3_import import (
        B3ImportBatch,
        B3ImportBatchStatus,
        B3ImportReportType,
    )

    batch = B3ImportBatch(
        id=uuid4(),
        file_name="movimentacao.xlsx",
        file_hash="abc",
        report_type=B3ImportReportType.MOVEMENT,
        total_rows=25,
        new_rows=4,
        duplicate_rows=10,
        review_rows=3,
        unsupported_rows=6,
        invalid_rows=2,
        status=B3ImportBatchStatus.COMPLETED,
        created_at=datetime(2026, 10, 1, tzinfo=UTC),
    )

    class Repository:
        def __init__(self, portfolio_id):
            self.portfolio_id = portfolio_id

        def list_batches(self, *, offset: int, limit: int):
            return ((batch,), 21)

    monkeypatch.setattr(dashboard, "SqliteB3ImportRepository", Repository)
    result = dashboard.list_b3_import_history(offset=20, page_size=20)

    assert result["total"] == 21
    assert result["has_more"] is False
    assert result["next_cursor"] is None
    assert result["items"][0]["file_name"] == "movimentacao.xlsx"
    assert result["items"][0]["status"] == "COMPLETED"
