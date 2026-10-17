"""Persist benchmark observations with their native semantics."""

import sqlalchemy as sa

from alembic import op

revision = "0002_benchmark_observations"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "benchmark_observations",
        sa.Column("benchmark", sa.String(32), primary_key=True),
        sa.Column("effective_date", sa.Date(), primary_key=True),
        sa.Column("nature", sa.String(32), nullable=False),
        sa.Column("value", sa.String(40), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("benchmark_observations")
