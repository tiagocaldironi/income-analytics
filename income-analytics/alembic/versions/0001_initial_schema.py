"""Initial persisted source-of-truth schema.

Revision ID: 0001_initial_schema
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticker", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("asset_class", sa.String(50), nullable=False),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("country", sa.String(16), nullable=False),
        sa.Column("sector", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "financial_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id")),
        sa.Column("quantity", sa.String(40)),
        sa.Column("unit_price", sa.String(40)),
        sa.Column("amount", sa.String(40)),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text()),
    )
    op.create_table(
        "market_prices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("price", sa.String(40), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "benchmark_rates",
        sa.Column("name", sa.String(32), primary_key=True),
        sa.Column("effective_date", sa.Date(), primary_key=True),
        sa.Column("return_percentage", sa.String(40), nullable=False),
    )
    op.create_table(
        "allocation_targets",
        sa.Column("asset_class", sa.String(50), primary_key=True),
        sa.Column("target", sa.String(40), nullable=False),
    )
    op.create_table(
        "asset_targets",
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id"), primary_key=True),
        sa.Column("target", sa.String(40), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "asset_targets",
        "allocation_targets",
        "benchmark_rates",
        "market_prices",
        "financial_events",
        "assets",
    ):
        op.drop_table(table)
