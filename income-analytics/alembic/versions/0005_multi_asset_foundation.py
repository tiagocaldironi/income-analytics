"""Add multi-asset wealth details without altering existing listed assets."""

import sqlalchemy as sa

from alembic import op

revision = "0005_multi_asset_foundation"
down_revision = "0004_provider_health"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("valuation_method", sa.String(50), nullable=True))
    op.execute("UPDATE assets SET valuation_method = 'MARKET_PRICE' WHERE valuation_method IS NULL")
    op.create_table(
        "fixed_income_details",
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id"), primary_key=True),
        sa.Column("instrument_type", sa.String(50), nullable=False),
        sa.Column("issuer", sa.String(200)),
        sa.Column("indexer_type", sa.String(50), nullable=False),
        sa.Column("contracted_rate", sa.String(40)),
        sa.Column("percentage_of_indexer", sa.String(40)),
        sa.Column("spread", sa.String(40)),
        sa.Column("application_date", sa.Date(), nullable=False),
        sa.Column("maturity_date", sa.Date()),
        sa.Column("principal_amount", sa.String(40), nullable=False),
        sa.Column("liquidity_type", sa.String(50)),
        sa.Column("tax_exempt", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "pension_plan_details",
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id"), primary_key=True),
        sa.Column("pension_type", sa.String(16), nullable=False),
        sa.Column("institution", sa.String(200), nullable=False),
        sa.Column("plan_name", sa.String(200), nullable=False),
        sa.Column("tax_regime", sa.String(32), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("reported_balance", sa.String(40), nullable=False),
        sa.Column("reported_balance_date", sa.Date(), nullable=False),
    )
    op.create_table(
        "real_estate_details",
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id"), primary_key=True),
        sa.Column("property_type", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("cep", sa.String(16), nullable=False),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(32)),
        sa.Column("neighborhood", sa.String(100)),
        sa.Column("usable_area_m2", sa.String(40)),
        sa.Column("bedrooms", sa.Integer()),
        sa.Column("parking_spaces", sa.Integer()),
        sa.Column("acquisition_date", sa.Date()),
        sa.Column("acquisition_value", sa.String(40)),
        sa.Column("current_manual_value", sa.String(40), nullable=False),
        sa.Column("valuation_date", sa.Date(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("real_estate_details")
    op.drop_table("pension_plan_details")
    op.drop_table("fixed_income_details")
    op.drop_column("assets", "valuation_method")
