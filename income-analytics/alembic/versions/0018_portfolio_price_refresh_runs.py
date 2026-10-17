"""Persist auditable outcomes for each portfolio market-price refresh."""

import sqlalchemy as sa

from alembic import op

revision = "0018_portfolio_price_refresh_runs"
down_revision = "0017_portfolio_market_price_lineage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_price_refresh_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("outcomes_json", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("market_price_refresh_runs")
