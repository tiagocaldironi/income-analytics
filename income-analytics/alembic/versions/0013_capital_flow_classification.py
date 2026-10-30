"""Persist capital-flow classifications for performance scopes."""

import sqlalchemy as sa

from alembic import op

revision = "0013_capital_flow_classification"
down_revision = "0012_pension_market_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("financial_events", sa.Column("metadata_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("financial_events", "metadata_json")
