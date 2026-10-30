"""Persist pension investment vehicles and their CVM quota history."""

import sqlalchemy as sa

from alembic import op

revision = "0012_pension_market_data"
down_revision = "0011_pension_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pension_investment_vehicles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pension_asset_id", sa.String(36), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("vehicle_name", sa.String(300), nullable=False),
        sa.Column("vehicle_cnpj", sa.String(14), nullable=False),
        sa.Column("vehicle_type", sa.String(16), nullable=False),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
    )
    op.create_table(
        "pension_fund_quotas",
        sa.Column(
            "vehicle_id",
            sa.String(36),
            sa.ForeignKey("pension_investment_vehicles.id"),
            nullable=False,
        ),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("quota", sa.String(48), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("vehicle_id", "reference_date"),
    )


def downgrade() -> None:
    op.drop_table("pension_fund_quotas")
    op.drop_table("pension_investment_vehicles")
