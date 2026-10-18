from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from income_analytics.application.b3_import import (
    B3ImportBatch,
    B3ImportBatchStatus,
    B3ImportReportType,
)
from income_analytics.application.paid_income import IncomeType, PaidIncomeEvent
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.asset_allocation_policy import AssetAllocationPolicy
from income_analytics.domain.entities.portfolio import Portfolio
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.infrastructure.sqlite_repositories import (
    SqliteAllocationPolicyRepository,
    SqliteAssetAllocationPolicyRepository,
    SqliteB3ImportRepository,
    SqliteFinancialEventRepository,
    SqliteImportedPaidIncomeRepository,
    SqlitePortfolioDashboardSnapshotRepository,
    SqlitePortfolioRepository,
)


def _portfolio(portfolio_id):
    now = datetime.now(UTC)
    portfolio = Portfolio(
        id=portfolio_id, name=f"Portfolio {portfolio_id}", created_at=now, updated_at=now
    )
    SqlitePortfolioRepository().save(portfolio)


def test_same_global_asset_events_targets_and_b3_batches_are_portfolio_scoped() -> None:
    portfolio_a, portfolio_b = uuid4(), uuid4()
    _portfolio(portfolio_a)
    _portfolio(portfolio_b)

    session_a = PortfolioSession(portfolio_id=portfolio_a, persistent=True)
    assert SqliteFinancialEventRepository(portfolio_a).list() == ()
    session_a.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="SCOPEV1",
        quantity=Decimal("2"),
        unit_price=Decimal("10"),
    )
    session_a.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="SCOPEV1",
        quantity=Decimal("3"),
        unit_price=Decimal("11"),
    )

    session_b = PortfolioSession(portfolio_id=portfolio_b, persistent=True)
    session_b.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="SCOPEV1",
        quantity=Decimal("1"),
        unit_price=Decimal("12"),
    )

    events_a = SqliteFinancialEventRepository(portfolio_a).list()
    events_b = SqliteFinancialEventRepository(portfolio_b).list()
    assert len(events_a) == 2
    assert len(events_b) == 1
    assert events_a[0].asset.id == events_b[0].asset.id
    assert session_a.project().positions[0].quantity.value == Decimal("5")
    assert session_b.project().positions[0].quantity.value == Decimal("1")

    session_a.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="SCOPEV2",
        quantity=Decimal("1"),
        unit_price=Decimal("10"),
    )
    session_b.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="SCOPEV2",
        quantity=Decimal("1"),
        unit_price=Decimal("10"),
    )
    shared_asset = session_a._assets["SCOPEV1"]
    SqliteAssetAllocationPolicyRepository(portfolio_a).save(
        AssetAllocationPolicy(
            targets={
                shared_asset.asset_class: {
                    "SCOPEV1": Decimal("0.7"),
                    "SCOPEV2": Decimal("0.3"),
                }
            }
        )
    )
    SqliteAssetAllocationPolicyRepository(portfolio_b).save(
        AssetAllocationPolicy(
            targets={
                shared_asset.asset_class: {
                    "SCOPEV1": Decimal("0.3"),
                    "SCOPEV2": Decimal("0.7"),
                }
            }
        )
    )
    policy_a = SqliteAssetAllocationPolicyRepository(portfolio_a).get()
    policy_b = SqliteAssetAllocationPolicyRepository(portfolio_b).get()
    assert policy_a.target_for(shared_asset) == Decimal("0.7")
    assert policy_b.target_for(shared_asset) == Decimal("0.3")

    session_a.update_market_price(
        ticker="SCOPEV1", current_price=Decimal("15"), effective_date=date(2026, 1, 3)
    )
    reloaded_b = PortfolioSession(portfolio_id=portfolio_b, persistent=True)
    shared_quote = next(
        item
        for item in reloaded_b.project(as_of=date(2026, 1, 3)).positions
        if str(item.asset.ticker) == "SCOPEV1"
    )
    assert shared_quote.current_price is not None
    assert shared_quote.current_price.amount == Decimal("15")

    # Exercise A-B-A and B-A-B with portfolio-derived read models.
    a_wealth_before = session_a.projections_at((date(2026, 1, 3),))
    b_wealth_before = reloaded_b.projections_at((date(2026, 1, 3),))
    a_performance_before = session_a.performance(
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 3)
    )
    b_performance_before = reloaded_b.performance(
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 3)
    )
    a_findings_before = session_a.intelligence(as_of=date(2026, 1, 3))
    b_findings_before = reloaded_b.intelligence(as_of=date(2026, 1, 3))
    assert session_a.projections_at((date(2026, 1, 3),)) == a_wealth_before
    assert reloaded_b.projections_at((date(2026, 1, 3),)) == b_wealth_before
    assert session_a.performance(start_date=date(2026, 1, 1), end_date=date(2026, 1, 3)) == (
        a_performance_before
    )
    assert reloaded_b.performance(start_date=date(2026, 1, 1), end_date=date(2026, 1, 3)) == (
        b_performance_before
    )
    assert session_a.intelligence(as_of=date(2026, 1, 3)) == a_findings_before
    assert reloaded_b.intelligence(as_of=date(2026, 1, 3)) == b_findings_before

    income = PaidIncomeEvent(
        asset_identifier="SCOPEV1",
        income_type=IncomeType.DIVIDEND,
        amount_per_unit=Decimal("0.50"),
        record_date=None,
        payment_date=None,
        approval_date=None,
        provider="fixture",
        provider_event_id="fixture-income",
    )
    SqliteImportedPaidIncomeRepository(portfolio_a).save(
        event=income,
        asset_id=str(session_a._assets["SCOPEV1"].id),
        import_status="IMPORTED",
        detail=None,
        eligible_quantity=Decimal("5"),
        calculated_amount=Decimal("2.50"),
        financial_event_id=None,
    )
    assert SqliteImportedPaidIncomeRepository(portfolio_a).find_by_fingerprint(income.fingerprint)
    assert (
        SqliteImportedPaidIncomeRepository(portfolio_b).find_by_fingerprint(income.fingerprint)
        is None
    )

    SqlitePortfolioDashboardSnapshotRepository(portfolio_a).save({"value": "A"})
    SqlitePortfolioDashboardSnapshotRepository(portfolio_b).save({"value": "B"})
    assert SqlitePortfolioDashboardSnapshotRepository(portfolio_a).get()["value"] == "A"
    assert SqlitePortfolioDashboardSnapshotRepository(portfolio_b).get()["value"] == "B"

    SqliteAllocationPolicyRepository(portfolio_a).save(
        AllocationPolicy(
            targets={
                AssetClass.BRAZILIAN_STOCK: Decimal("0.25"),
                AssetClass.BRAZILIAN_ETF: Decimal("0.75"),
            }
        )
    )
    SqliteAllocationPolicyRepository(portfolio_b).save(
        AllocationPolicy(
            targets={
                AssetClass.BRAZILIAN_STOCK: Decimal("0.75"),
                AssetClass.BRAZILIAN_ETF: Decimal("0.25"),
            }
        )
    )
    assert SqliteAllocationPolicyRepository(portfolio_a).get().targets[
        AssetClass.BRAZILIAN_STOCK
    ] == Decimal("0.25")
    assert SqliteAllocationPolicyRepository(portfolio_b).get().targets[
        AssetClass.BRAZILIAN_STOCK
    ] == Decimal("0.75")

    batch = B3ImportBatch(
        id=uuid4(),
        file_name="scope.xlsx",
        file_hash="scope",
        report_type=B3ImportReportType.MOVEMENT,
        total_rows=0,
        new_rows=0,
        duplicate_rows=0,
        review_rows=0,
        unsupported_rows=0,
        invalid_rows=0,
        status=B3ImportBatchStatus.PREVIEWED,
        created_at=datetime.now(UTC),
    )
    SqliteB3ImportRepository(portfolio_a).create_batch(batch)
    assert SqliteB3ImportRepository(portfolio_a).get_batch(batch.id) is not None
    assert SqliteB3ImportRepository(portfolio_b).get_batch(batch.id) is None
