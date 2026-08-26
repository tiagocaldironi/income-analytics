"""SQLite adapters; mapping between persistence records and domain entities."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.asset_allocation_policy import AssetAllocationPolicy
from income_analytics.domain.benchmark_rate import BenchmarkRate
from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.entities.currency import Currency
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.entities.institution import Institution
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.market_price import MarketPrice
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from income_analytics.domain.value_objects.ticker import Ticker
from income_analytics.infrastructure.database import SessionFactory, initialize_database
from income_analytics.infrastructure.models import (
    AllocationTargetRecord,
    AssetRecord,
    AssetTargetRecord,
    BenchmarkRateRecord,
    FinancialEventRecord,
    MarketPriceRecord,
)


class SqliteAssetRepository:
    def save(self, asset: Asset) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                AssetRecord(
                    id=str(asset.id),
                    ticker=str(asset.ticker),
                    name=asset.name,
                    asset_class=asset.asset_class.value,
                    asset_type=asset.asset_type.value,
                    currency_code=asset.currency.code,
                    country=asset.country,
                    sector=asset.sector,
                    created_at=asset.created_at,
                )
            )

    def get_by_ticker(self, ticker: str) -> Asset | None:
        with SessionFactory() as session:
            record = (
                session.query(AssetRecord).filter_by(ticker=ticker.strip().upper()).one_or_none()
            )
            return self._to_domain(record) if record else None

    def list(self) -> tuple[Asset, ...]:
        with SessionFactory() as session:
            return tuple(self._to_domain(record) for record in session.query(AssetRecord).all())

    @staticmethod
    def _to_domain(record: AssetRecord) -> Asset:
        created_at = SqliteAssetRepository._utc(record.created_at)
        return Asset(
            id=UUID(record.id),
            ticker=Ticker(record.ticker),
            name=record.name,
            asset_type=AssetType(record.asset_type),
            asset_class=AssetClass(record.asset_class),
            currency=Currency(
                code=record.currency_code,
                name=record.currency_code,
                symbol=record.currency_code,
                decimal_places=2,
            ),
            institution=Institution(name="Cadastro local"),
            country=record.country,
            sector=record.sector,
            created_at=created_at,
            updated_at=created_at,
        )

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class SqliteFinancialEventRepository:
    def save(self, event: FinancialEvent) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                FinancialEventRecord(
                    id=str(event.id),
                    account_id=str(event.account_id),
                    event_type=event.event_type.value,
                    asset_id=str(event.asset.id) if event.asset else None,
                    quantity=str(event.quantity.value) if event.quantity else None,
                    unit_price=str(event.unit_price.amount) if event.unit_price else None,
                    amount=str(event.amount.amount) if event.amount else None,
                    effective_date=event.effective_date,
                    occurred_at=event.occurred_at,
                    registered_at=event.registered_at,
                    description=event.description,
                )
            )

    def list(self) -> tuple[FinancialEvent, ...]:
        assets = {str(asset.id): asset for asset in SqliteAssetRepository().list()}
        with SessionFactory() as session:
            rows = (
                session.query(FinancialEventRecord)
                .order_by(
                    FinancialEventRecord.effective_date,
                    FinancialEventRecord.registered_at,
                    FinancialEventRecord.id,
                )
                .all()
            )
        return tuple(
            FinancialEvent(
                id=UUID(row.id),
                account_id=UUID(row.account_id),
                event_type=FinancialEventType(row.event_type),
                asset=assets.get(row.asset_id) if row.asset_id else None,
                quantity=Quantity(Decimal(row.quantity)) if row.quantity else None,
                unit_price=Money(Decimal(row.unit_price)) if row.unit_price else None,
                amount=Money(Decimal(row.amount)) if row.amount else None,
                effective_date=row.effective_date,
                occurred_at=SqliteAssetRepository._utc(row.occurred_at),
                registered_at=SqliteAssetRepository._utc(row.registered_at),
                description=row.description,
            )
            for row in rows
        )


class SqliteMarketPriceRepository:
    def save(self, price: MarketPrice) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                MarketPriceRecord(
                    id=str(price.id),
                    asset_id=str(price.asset.id),
                    price=str(price.price.amount),
                    effective_date=price.effective_date,
                    registered_at=price.registered_at,
                )
            )

    def list(self) -> tuple[MarketPrice, ...]:
        assets = {str(asset.id): asset for asset in SqliteAssetRepository().list()}
        with SessionFactory() as session:
            rows = (
                session.query(MarketPriceRecord)
                .order_by(
                    MarketPriceRecord.effective_date,
                    MarketPriceRecord.registered_at,
                    MarketPriceRecord.id,
                )
                .all()
            )
        return tuple(
            MarketPrice(
                id=UUID(row.id),
                asset=assets[row.asset_id],
                price=Money(Decimal(row.price)),
                effective_date=row.effective_date,
                registered_at=SqliteAssetRepository._utc(row.registered_at),
            )
            for row in rows
        )


class SqliteBenchmarkRateRepository:
    def save(self, rate: BenchmarkRate) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                BenchmarkRateRecord(
                    name=rate.name,
                    effective_date=rate.effective_date,
                    return_percentage=str(rate.return_percentage),
                )
            )

    def list(self) -> tuple[BenchmarkRate, ...]:
        with SessionFactory() as session:
            rows = (
                session.query(BenchmarkRateRecord)
                .order_by(BenchmarkRateRecord.name, BenchmarkRateRecord.effective_date)
                .all()
            )
        return tuple(
            BenchmarkRate(
                name=row.name,
                effective_date=row.effective_date,
                return_percentage=Decimal(row.return_percentage),
            )
            for row in rows
        )


class SqliteAllocationPolicyRepository:
    def save(self, policy: AllocationPolicy) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.query(AllocationTargetRecord).delete()
            session.add_all(
                AllocationTargetRecord(asset_class=key.value, target=str(value))
                for key, value in policy.targets.items()
            )

    def get(self) -> AllocationPolicy | None:
        from income_analytics.domain.enums.asset_class import AssetClass

        with SessionFactory() as session:
            rows = session.query(AllocationTargetRecord).all()
        return (
            AllocationPolicy(
                targets={AssetClass(row.asset_class): Decimal(row.target) for row in rows}
            )
            if rows
            else None
        )


class SqliteAssetAllocationPolicyRepository:
    def save(self, policy: AssetAllocationPolicy) -> None:
        initialize_database()
        assets = {str(asset.ticker): asset for asset in SqliteAssetRepository().list()}
        with SessionFactory.begin() as session:
            session.query(AssetTargetRecord).delete()
            for targets in policy.targets.values():
                for ticker, target in targets.items():
                    session.add(
                        AssetTargetRecord(asset_id=str(assets[ticker].id), target=str(target))
                    )

    def get(self) -> AssetAllocationPolicy | None:
        assets = {str(asset.id): asset for asset in SqliteAssetRepository().list()}
        with SessionFactory() as session:
            rows = session.query(AssetTargetRecord).all()
        if not rows:
            return None
        targets: dict[AssetClass, dict[str, Decimal]] = {}
        for row in rows:
            asset = assets[row.asset_id]
            targets.setdefault(asset.asset_class, {})[str(asset.ticker)] = Decimal(row.target)
        return AssetAllocationPolicy(targets=targets)
