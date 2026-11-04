"""Typed presentation facets; financial class identities remain unchanged."""

from datetime import date, datetime
from decimal import Decimal
from typing import TypedDict


class TreasuryPresentation(TypedDict, total=False):
    display_group: str
    display_name: str
    quantity_unit: str
    treasury_trade_supported: bool


class HoldingRow(TreasuryPresentation, total=False):
    asset_id: str
    ticker: str
    name: str
    country: str
    sector: str | None
    currency_code: str
    quantity: Decimal
    average_price: Decimal
    current_price: Decimal | None
    price_as_of: date | None
    price_provider: str | None
    price_retrieved_at: datetime | None
    price_timestamp: datetime | None
    market_value: Decimal | None
    market_value_base: Decimal | None
    total_result: Decimal | None
    return_percentage: Decimal | None
    income_received: Decimal
    portfolio_weight: Decimal | None
    class_weight: Decimal | None
    target_weight: Decimal | None
    instrument: str | None
    indexer: str | None
    condition: str | None
    contract_key: str | None
    contract_label: str | None
    display_label: str
    current_value: Decimal | None
    current_weight_in_class: Decimal | None
    gap_pp: Decimal | None
    target_weight_total_portfolio: Decimal | None
    target_only: bool


class HoldingGroup(TypedDict, total=False):
    asset_class: str
    label: str
    asset_count: int
    market_value: Decimal | None
    total_cost: Decimal | None
    weight: Decimal | None
    total_result: Decimal | None
    target_weight: Decimal | None
    deviation: Decimal | None
    performance_coverage: dict[str, object] | None
    assets: list[HoldingRow]
    composition_distance: Decimal | None
    valuation_quality: str
    valuation_unavailable_reason: str | None
    financial_asset_class: str
    shared_strategy_note: str
