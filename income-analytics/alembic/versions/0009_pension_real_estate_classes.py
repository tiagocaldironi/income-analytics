"""Promote pension and real estate to explicit wealth classes."""

import sqlalchemy as sa
from alembic import op

revision = "0009_pension_real_estate_classes"
down_revision = "0008_paid_income_brapi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pension_columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("pension_plan_details")}
    if "institution_cnpj" not in pension_columns:
        op.add_column("pension_plan_details", sa.Column("institution_cnpj", sa.String(14)))
    estate_columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("real_estate_details")}
    if "country" not in estate_columns:
        op.add_column("real_estate_details", sa.Column("country", sa.String(16), server_default="BR", nullable=False))
    if "ownership_percentage" not in estate_columns:
        op.add_column("real_estate_details", sa.Column("ownership_percentage", sa.String(40), server_default="100", nullable=False))
    op.execute("UPDATE assets SET asset_class = 'PENSION' WHERE asset_type = 'PENSION'")
    op.execute("UPDATE assets SET asset_class = 'REAL_ESTATE' WHERE asset_type = 'REAL_ESTATE'")


def downgrade() -> None:
    op.execute("UPDATE assets SET asset_class = 'OTHER' WHERE asset_class IN ('PENSION', 'REAL_ESTATE')")
