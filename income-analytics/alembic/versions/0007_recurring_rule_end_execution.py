"""Add an optional end date to recurring instructions."""

import sqlalchemy as sa

from alembic import op

revision = "0007_recurring_rule_end_execution"
down_revision = "0006_recurring_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("recurring_rules")
    }
    if "end_execution_date" not in columns:
        op.add_column("recurring_rules", sa.Column("end_execution_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("recurring_rules", "end_execution_date")
