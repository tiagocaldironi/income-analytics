"""Store separate Income Starter approval identities and publication actor."""

import sqlalchemy as sa

from alembic import op

revision = "0022_income_starter_review_evidence"
down_revision = "0021_income_starter_draft_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "income_starter_template_versions",
        sa.Column("financial_approved_by", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "income_starter_template_versions",
        sa.Column("financial_approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "income_starter_template_versions",
        sa.Column("regulatory_approved_by", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "income_starter_template_versions",
        sa.Column("regulatory_approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "income_starter_template_versions",
        sa.Column("published_by", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("income_starter_template_versions", "published_by")
    op.drop_column("income_starter_template_versions", "regulatory_approved_at")
    op.drop_column("income_starter_template_versions", "regulatory_approved_by")
    op.drop_column("income_starter_template_versions", "financial_approved_at")
    op.drop_column("income_starter_template_versions", "financial_approved_by")
