"""Key pension quota history by the shared CVM vehicle identifier."""

import sqlalchemy as sa

from alembic import op

revision = "0020_shared_pension_quota_identity"
down_revision = "0019_portfolio_domain_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_portfolios_active_name_nocase",
        "portfolios",
        [sa.text("name COLLATE NOCASE")],
        unique=True,
        sqlite_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_table(
        "pension_fund_quotas_shared",
        sa.Column("vehicle_cnpj", sa.String(14), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("quota", sa.String(48), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("vehicle_cnpj", "reference_date"),
    )
    op.execute(
        sa.text(
            "INSERT OR REPLACE INTO pension_fund_quotas_shared "
            "(vehicle_cnpj, reference_date, quota, source, retrieved_at) "
            "SELECT v.vehicle_cnpj, q.reference_date, q.quota, q.source, q.retrieved_at "
            "FROM pension_fund_quotas q "
            "JOIN pension_investment_vehicles v ON v.id = q.vehicle_id"
        )
    )
    op.drop_table("pension_fund_quotas")
    op.rename_table("pension_fund_quotas_shared", "pension_fund_quotas")


def downgrade() -> None:
    op.drop_index("uq_portfolios_active_name_nocase", table_name="portfolios")
    op.create_table(
        "pension_fund_quotas_legacy",
        sa.Column(
            "vehicle_id",
            sa.String(36),
            sa.ForeignKey("pension_investment_vehicles.id"),
            nullable=False,
        ),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("quota", sa.String(48), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("vehicle_id", "reference_date"),
    )
    op.execute(
        sa.text(
            "INSERT OR REPLACE INTO pension_fund_quotas_legacy "
            "(vehicle_id, reference_date, quota, source, retrieved_at) "
            "SELECT v.id, q.reference_date, q.quota, q.source, q.retrieved_at "
            "FROM pension_fund_quotas q "
            "JOIN pension_investment_vehicles v ON v.vehicle_cnpj = q.vehicle_cnpj"
        )
    )
    op.drop_table("pension_fund_quotas")
    op.rename_table("pension_fund_quotas_legacy", "pension_fund_quotas")
