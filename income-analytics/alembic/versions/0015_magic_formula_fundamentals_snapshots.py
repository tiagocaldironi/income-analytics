"""Persist immutable normalized Magic Formula fundamentals."""

import sqlalchemy as sa
from alembic import op

revision = "0015_magic_formula_fundamentals_snapshots"
down_revision = "0014_b3_import_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "magic_formula_fundamentals_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("issuer_id", sa.String(64), nullable=False, index=True),
        sa.Column("financial_reference_date", sa.Date(), nullable=False),
        sa.Column("market_reference_date", sa.Date(), nullable=False),
        sa.Column("statement_type", sa.String(16), nullable=False),
        sa.Column("statement_scope", sa.String(16), nullable=False),
        sa.Column("adapter_version", sa.String(64), nullable=False),
        sa.Column("normalization_status", sa.String(48), nullable=False),
        sa.Column("validation_status", sa.String(32), nullable=False),
        sa.Column("metrics_json", sa.Text(), nullable=False),
        sa.Column("lineage_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("issuer_id", "financial_reference_date", "market_reference_date", "adapter_version", name="uq_magic_formula_snapshot_version"),
    )
    op.create_table(
        "company_normalization_validations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("issuer_id", sa.String(64), nullable=False, index=True),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("adapter_version", sa.String(64), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("expected_value", sa.String(64), nullable=False),
        sa.Column("actual_value", sa.String(64), nullable=False),
        sa.Column("difference", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("company_normalization_validations")
    op.drop_table("magic_formula_fundamentals_snapshots")
