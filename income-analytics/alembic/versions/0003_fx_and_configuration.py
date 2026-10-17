"""Persist FX observations and base-currency configuration."""

import sqlalchemy as sa

from alembic import op

revision = "0003_fx_and_configuration"
down_revision = "0002_benchmark_observations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fx_rates",
        sa.Column("base_currency", sa.String(12), primary_key=True),
        sa.Column("quote_currency", sa.String(12), primary_key=True),
        sa.Column("effective_date", sa.Date(), primary_key=True),
        sa.Column("rate", sa.String(40), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
    )
    op.create_table(
        "portfolio_configuration",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.String(64), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("portfolio_configuration")
    op.drop_table("fx_rates")
