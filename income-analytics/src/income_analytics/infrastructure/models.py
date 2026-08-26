"""SQLAlchemy tables for persisted source-of-truth records."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from income_analytics.infrastructure.database import Base


class AssetRecord(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    asset_class: Mapped[str] = mapped_column(String(50))
    asset_type: Mapped[str] = mapped_column(String(50))
    currency_code: Mapped[str] = mapped_column(String(3))
    country: Mapped[str] = mapped_column(String(16))
    sector: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FinancialEventRecord(Base):
    __tablename__ = "financial_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"))
    quantity: Mapped[str | None] = mapped_column(String(40))
    unit_price: Mapped[str | None] = mapped_column(String(40))
    amount: Mapped[str | None] = mapped_column(String(40))
    effective_date: Mapped[date] = mapped_column(Date)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text)


class MarketPriceRecord(Base):
    __tablename__ = "market_prices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    price: Mapped[str] = mapped_column(String(40))
    effective_date: Mapped[date] = mapped_column(Date, index=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BenchmarkRateRecord(Base):
    __tablename__ = "benchmark_rates"
    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    effective_date: Mapped[date] = mapped_column(Date, primary_key=True)
    return_percentage: Mapped[str] = mapped_column(String(40))


class AllocationTargetRecord(Base):
    __tablename__ = "allocation_targets"
    asset_class: Mapped[str] = mapped_column(String(50), primary_key=True)
    target: Mapped[str] = mapped_column(String(40))


class AssetTargetRecord(Base):
    __tablename__ = "asset_targets"
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), primary_key=True)
    target: Mapped[str] = mapped_column(String(40))
