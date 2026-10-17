"""Persist recurring event instructions."""

import sqlalchemy as sa

from alembic import op

revision = "0006_recurring_rules"
down_revision = "0005_multi_asset_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A previous interrupted local startup can have created the table before
    # Alembic records this revision.  The schema is exactly this revision's
    # schema, so preserve it and complete the version transition.
    if sa.inspect(op.get_bind()).has_table("recurring_rules"):
        return
    op.create_table(
        "recurring_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("amount", sa.String(40), nullable=False),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id")),
        sa.Column("frequency", sa.String(16), nullable=False),
        sa.Column("next_execution_date", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_table("recurring_rules")
