"""Add disabled-by-default BRAPI paid-income integration state."""

import sqlalchemy as sa
from alembic import op

revision = "0008_paid_income_brapi"
down_revision = "0007_recurring_rule_end_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paid_income_provider_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("api_token", sa.Text()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_result", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "imported_paid_income",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_event_id", sa.String(160)),
        sa.Column("raw_fingerprint", sa.String(128), nullable=False, unique=True),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("income_type", sa.String(32), nullable=False),
        sa.Column("record_date", sa.Date()),
        sa.Column("payment_date", sa.Date()),
        sa.Column("amount_per_unit", sa.String(40), nullable=False),
        sa.Column("eligible_quantity", sa.String(40)),
        sa.Column("calculated_amount", sa.String(40)),
        sa.Column("financial_event_id", sa.String(36), sa.ForeignKey("financial_events.id")),
        sa.Column("import_status", sa.String(32), nullable=False),
        sa.Column("detail", sa.Text()),
        sa.Column("imported_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_imported_paid_income_provider_event",
        "imported_paid_income",
        ["provider", "provider_event_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_imported_paid_income_provider_event", table_name="imported_paid_income")
    op.drop_table("imported_paid_income")
    op.drop_table("paid_income_provider_settings")
