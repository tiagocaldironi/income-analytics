"""Persist auditable B3 import batches and source-row identities."""

import sqlalchemy as sa
from alembic import op


revision = "0014_b3_import_audit"
down_revision = "0013_capital_flow_classification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "b3_import_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="B3"),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("file_hash", sa.String(128), nullable=False, index=True),
        sa.Column("report_type", sa.String(32), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unsupported_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "b3_imported_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("b3_import_batches.id"), nullable=False, index=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="B3"),
        sa.Column("fingerprint", sa.String(128), nullable=False, index=True),
        sa.Column("occurrence_index", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("event_date", sa.Date()),
        sa.Column("event_type", sa.String(32)),
        sa.Column("income_type", sa.String(32)),
        sa.Column("source_symbol", sa.String(32)),
        sa.Column("normalized_symbol", sa.String(32), index=True),
        sa.Column("institution", sa.String(200)),
        sa.Column("market", sa.String(80)),
        sa.Column("quantity", sa.String(40)),
        sa.Column("unit_price", sa.String(40)),
        sa.Column("total_value", sa.String(40)),
        sa.Column("raw_payload", sa.Text()),
        sa.Column("detail", sa.Text()),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id")),
        sa.Column("financial_event_id", sa.String(36), sa.ForeignKey("financial_events.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("source", "fingerprint", "occurrence_index", name="uq_b3_imported_record_identity"),
    )


def downgrade() -> None:
    op.drop_table("b3_imported_records")
    op.drop_table("b3_import_batches")
