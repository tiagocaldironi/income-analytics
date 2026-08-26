"""HTTP endpoints for the local portfolio dashboard."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.projectors.asset_rebalancing_projector import AssetAllocationStrategy
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection
from income_analytics.domain.value_objects.money import Money

router = APIRouter(prefix="/api", tags=["Portfolio"])
session = PortfolioSession()


class TradeInput(BaseModel):
    event_type: Literal["BUY", "SELL"]
    ticker: str = Field(min_length=1, max_length=12)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    effective_date: date
    asset_class: AssetClass


class MarketPriceInput(BaseModel):
    current_price: Decimal = Field(gt=0)
    effective_date: date


class DividendInput(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    amount: Decimal = Field(gt=0)
    effective_date: date


class ExternalFlowInput(BaseModel):
    event_type: Literal["DEPOSIT", "WITHDRAWAL"]
    amount: Decimal = Field(gt=0)
    effective_date: date


class BenchmarkRateInput(BaseModel):
    return_percentage: Decimal = Field(gt=Decimal("-1"))
    effective_date: date


class AssetClassInput(BaseModel):
    asset_class: AssetClass


class AssetInput(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=200)
    asset_class: AssetClass


class AllocationPolicyInput(BaseModel):
    targets: dict[AssetClass, Decimal]


class ContributionSimulationInput(BaseModel):
    amount: Decimal = Field(gt=0)


class AssetRebalancingInput(BaseModel):
    asset_class: AssetClass
    amount: Decimal = Field(gt=0)
    strategy: AssetAllocationStrategy


def serialize_portfolio(projection: PortfolioProjection) -> dict[str, object]:
    return {
        "cash": projection.cash.amount,
        "total_cost": projection.total_cost.amount,
        "realized_result": projection.total_realized_result.amount,
        "income_received": projection.income_received.amount,
        "total_contributions": projection.total_contributions.amount,
        "total_withdrawals": projection.total_withdrawals.amount,
        "net_external_flow": projection.net_external_flow.amount,
        "portfolio_equity": (
            projection.portfolio_equity.amount if projection.has_complete_market_data else None
        ),
        "total_market_value": (
            projection.total_market_value.amount if projection.has_complete_market_data else None
        ),
        "unrealized_result": projection.total_unrealized_result.amount,
        "total_result": projection.total_result.amount,
        "positions": [
            {
                "ticker": str(position.asset.ticker),
                "quantity": position.quantity.value,
                "cost": position.cost.amount,
                "average_price": position.average_price.amount,
                "realized_result": position.realized_result.amount,
                "current_price": (
                    position.current_price.amount if position.current_price else None
                ),
                "market_value": position.market_value.amount,
                "unrealized_result": position.unrealized_result.amount,
                "unrealized_return_percentage": position.unrealized_return_percentage,
                "income_received": position.income_received.amount,
                "total_result": position.total_result.amount,
            }
            for position in projection.positions
        ],
        "history": [
            {
                "type": event.event_type.value,
                "ticker": str(event.asset.ticker) if event.asset else "",
                "quantity": event.quantity.value if event.quantity else Decimal("0"),
                "unit_price": event.unit_price.amount if event.unit_price else Decimal("0"),
                "total": event.total_amount.amount,
                "effective_date": event.effective_date,
            }
            for event in session.history()
        ],
    }


@router.get("/portfolio")
def get_portfolio(as_of: date | None = None) -> dict[str, object]:
    return serialize_portfolio(session.projection(as_of=as_of))


@router.post("/trades", status_code=status.HTTP_201_CREATED)
def create_trade(trade: TradeInput) -> dict[str, object]:
    try:
        projection = session.register_trade(
            event_type=FinancialEventType(trade.event_type),
            ticker=trade.ticker,
            asset_class=trade.asset_class,
            quantity=trade.quantity,
            unit_price=trade.unit_price,
            effective_date=trade.effective_date,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return serialize_portfolio(projection)


@router.put("/market-prices/{ticker}")
def update_market_price(
    ticker: str,
    market_price: MarketPriceInput,
) -> dict[str, object]:
    try:
        projection = session.update_market_price(
            ticker=ticker,
            current_price=market_price.current_price,
            effective_date=market_price.effective_date,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return serialize_portfolio(projection)


@router.post("/dividends", status_code=status.HTTP_201_CREATED)
def create_dividend(dividend: DividendInput) -> dict[str, object]:
    try:
        projection = session.register_dividend(
            ticker=dividend.ticker,
            amount=dividend.amount,
            effective_date=dividend.effective_date,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return serialize_portfolio(projection)


@router.post("/external-flows", status_code=status.HTTP_201_CREATED)
def create_external_flow(flow: ExternalFlowInput) -> dict[str, object]:
    try:
        projection = session.register_external_flow(
            event_type=FinancialEventType(flow.event_type),
            amount=flow.amount,
            effective_date=flow.effective_date,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    return serialize_portfolio(projection)


@router.get("/portfolio/performance")
def get_portfolio_performance(start_date: date, end_date: date) -> dict[str, object]:
    try:
        performance = session.performance(start_date=start_date, end_date=end_date)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    return {
        "start_date": performance.start_date,
        "end_date": performance.end_date,
        "beginning_equity": performance.beginning_equity.amount
        if performance.beginning_equity
        else None,
        "ending_equity": performance.ending_equity.amount if performance.ending_equity else None,
        "total_contributions": performance.total_contributions.amount,
        "total_withdrawals": performance.total_withdrawals.amount,
        "net_external_flow": performance.net_external_flow.amount,
        "twr": performance.twr,
        "xirr": performance.xirr,
        "unavailable_reason": performance.unavailable_reason,
        "periods": [
            {
                "start_date": period.start_date,
                "end_date": period.end_date,
                "return_percentage": period.return_percentage,
            }
            for period in performance.periods
        ],
    }


@router.post("/benchmarks/{name}", status_code=status.HTTP_201_CREATED)
def create_benchmark_rate(name: str, benchmark: BenchmarkRateInput) -> dict[str, str]:
    try:
        session.register_benchmark_rate(
            name=name,
            return_percentage=benchmark.return_percentage,
            effective_date=benchmark.effective_date,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {"status": "registered"}


@router.get("/portfolio/risk")
def get_portfolio_risk(start_date: date, end_date: date) -> dict[str, object]:
    try:
        risk = session.risk(start_date=start_date, end_date=end_date)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {
        "start_date": risk.start_date,
        "end_date": risk.end_date,
        "frequency": risk.frequency,
        "observations": len(risk.returns),
        "periodic_volatility": risk.periodic_volatility,
        "annualized_volatility": risk.annualized_volatility,
        "maximum_drawdown": risk.maximum_drawdown,
        "peak_date": risk.peak_date,
        "trough_date": risk.trough_date,
        "recovery_date": risk.recovery_date,
        "sharpe_ratio": risk.sharpe_ratio,
        "sharpe_unavailable_reason": risk.sharpe_unavailable_reason,
    }


@router.get("/portfolio/allocation")
def get_portfolio_allocation(as_of: date | None = None) -> dict[str, object]:
    allocation = session.allocation(as_of=as_of)
    return {
        "portfolio_market_value": allocation.portfolio_market_value.amount,
        "valued_assets": allocation.valued_assets,
        "total_open_assets": allocation.total_open_assets,
        "valuation_coverage": allocation.valuation_coverage,
        "largest_position_weight": allocation.largest_position_weight,
        "top_3_weight": allocation.top_3_weight,
        "top_5_weight": allocation.top_5_weight,
        "hhi": allocation.hhi,
        "assets": [
            {
                "ticker": str(asset.position.asset.ticker),
                "market_value": asset.position.market_value.amount
                if asset.position.current_price
                else None,
                "portfolio_weight": asset.portfolio_weight,
                "total_result": asset.position.total_result.amount,
                "result_contribution_share": asset.result_contribution_share,
                "is_open": not asset.position.is_empty,
            }
            for asset in allocation.assets
        ],
    }


@router.put("/assets/{ticker}/class")
def update_asset_class(ticker: str, classification: AssetClassInput) -> dict[str, str]:
    try:
        session.update_asset_class(ticker=ticker, asset_class=classification.asset_class)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {"status": "updated"}


@router.get("/portfolio/class-allocation")
def get_portfolio_class_allocation(as_of: date | None = None) -> dict[str, object]:
    allocation = session.class_allocation(as_of=as_of)
    return {
        "classification_coverage": allocation.classification_coverage,
        "classification_coverage_by_value": allocation.classification_coverage_by_value,
        "largest_class": allocation.largest_class,
        "largest_class_weight": allocation.largest_class_weight,
        "class_hhi": allocation.class_hhi,
        "classes": [
            {
                "asset_class": item.asset_class,
                "market_value": item.market_value.amount,
                "weight": item.weight,
                "asset_count": item.asset_count,
                "total_result": item.total_result.amount,
                "income_received": item.income_received.amount,
                "result_contribution_share": item.result_contribution_share,
            }
            for item in allocation.classes
        ],
    }


@router.put("/allocation-policy")
def set_allocation_policy(policy: AllocationPolicyInput) -> dict[str, str]:
    try:
        session.set_allocation_policy(AllocationPolicy(targets=policy.targets))
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {"status": "updated"}


@router.get("/portfolio/allocation-analysis")
def get_allocation_analysis(as_of: date | None = None) -> dict[str, object]:
    try:
        analysis = session.allocation_analysis(as_of=as_of)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {
        "portfolio_drift": analysis.portfolio_drift,
        "portfolio_drift_value": analysis.portfolio_drift_value.amount,
        "comparisons": [
            {
                "asset_class": item.asset_class,
                "current_weight": item.current_weight,
                "target_weight": item.target_weight,
                "deviation": item.deviation,
                "value_deviation": item.value_deviation.amount,
                "status": item.status,
            }
            for item in analysis.comparisons
        ],
    }


@router.get("/portfolio/rebalancing")
def get_rebalancing(as_of: date | None = None) -> dict[str, object]:
    try:
        plan = session.rebalancing(as_of=as_of)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {
        "mode": "FULL_REBALANCING",
        "total_excess": plan.total_excess.amount,
        "total_deficit": plan.total_deficit.amount,
        "classes": [
            {
                "asset_class": item.asset_class,
                "excess_value": max(item.value_deviation.amount, Decimal("0")),
                "deficit_value": max(-item.value_deviation.amount, Decimal("0")),
                "status": item.status,
            }
            for item in plan.analysis.comparisons
        ],
    }


@router.post("/portfolio/rebalancing/contribution-only")
def simulate_contribution_rebalancing(simulation: ContributionSimulationInput) -> dict[str, object]:
    try:
        plan = session.rebalancing()
        allocations = plan.contribution_only(Money(simulation.amount))
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {
        "mode": "CONTRIBUTION_ONLY_REBALANCING",
        "contribution": simulation.amount,
        "allocations": [
            {"asset_class": asset_class, "simulated_amount": amount.amount}
            for asset_class, amount in allocations
        ],
        "notice": "Simulação analítica; nenhuma ordem será executada.",
    }


@router.post("/portfolio/rebalancing/assets")
def simulate_asset_rebalancing(simulation: AssetRebalancingInput) -> dict[str, object]:
    allocations = session.asset_rebalancing(
        asset_class=simulation.asset_class,
        amount=simulation.amount,
        strategy=simulation.strategy,
    )
    return {
        "strategy": simulation.strategy,
        "allocations": [
            {"ticker": ticker, "simulated_amount": amount.amount} for ticker, amount in allocations
        ],
        "notice": "Simulação analítica; nenhuma ordem será executada.",
    }


@router.get("/portfolio/history")
def get_portfolio_history() -> dict[str, object]:
    history = session.portfolio_history()
    return {
        "snapshots": [
            {
                "effective_date": snapshot.effective_date,
                "total_cost": snapshot.portfolio.total_cost.amount,
                "market_value": (
                    snapshot.portfolio.total_market_value.amount
                    if snapshot.portfolio.has_complete_market_data
                    else None
                ),
                "cash": snapshot.portfolio.cash.amount,
                "realized_result": snapshot.portfolio.total_realized_result.amount,
                "unrealized_result": snapshot.portfolio.total_unrealized_result.amount,
                "income_received": snapshot.portfolio.income_received.amount,
                "total_result": snapshot.portfolio.total_result.amount,
            }
            for snapshot in history.snapshots
        ]
    }


@router.delete("/portfolio", status_code=status.HTTP_204_NO_CONTENT)
def clear_portfolio() -> None:
    session.clear()
