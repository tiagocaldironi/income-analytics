"""Store quote provenance and provider timestamp for portfolio market prices."""

import sqlalchemy as sa

from alembic import op

revision = "0017_portfolio_market_price_lineage"
down_revision = "0016_magic_formula_canonical_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "market_prices",
        sa.Column("provider", sa.String(64), nullable=False, server_default="manual"),
    )
    op.add_column("market_prices", sa.Column("price_timestamp", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("market_prices", "price_timestamp")
    op.drop_column("market_prices", "provider")
