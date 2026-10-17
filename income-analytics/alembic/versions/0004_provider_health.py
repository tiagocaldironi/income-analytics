"""Persist last-known health for data providers."""

import sqlalchemy as sa

from alembic import op

revision = "0004_provider_health"
down_revision = "0003_fx_and_configuration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_health",
        sa.Column("provider", sa.String(64), primary_key=True),
        sa.Column("last_success", sa.DateTime(timezone=True)),
        sa.Column("last_failure", sa.DateTime(timezone=True)),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_type", sa.String(80)),
    )


def downgrade() -> None:
    op.drop_table("provider_health")
