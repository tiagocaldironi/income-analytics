"""Add the persisted dashboard read model."""

import sqlalchemy as sa
from alembic import op

revision = "0010_portfolio_dashboard_snapshot"
down_revision = "0009_pension_real_estate_classes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_dashboard_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("portfolio_dashboard_snapshot")
