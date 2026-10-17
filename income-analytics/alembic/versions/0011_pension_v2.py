"""Expand pension details without changing the identity of existing plans."""

import sqlalchemy as sa

from alembic import op

revision = "0011_pension_v2"
down_revision = "0010_portfolio_dashboard_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("pension_plan_details")
    }
    columns = (
        ("ownership_origin", sa.String(16), "'PARTICULAR'"),
        ("pension_system_type", sa.String(16), "'OPEN'"),
        ("product_type", sa.String(16), None),
        ("closed_plan_modality", sa.String(16), None),
        ("sponsor_name", sa.String(200), None),
        ("sponsor_cnpj", sa.String(14), None),
        ("susep_process_number", sa.String(80), None),
        ("cnpb", sa.String(80), None),
        ("participant_balance", sa.String(40), None),
        ("sponsor_balance", sa.String(40), None),
        ("employer_match_enabled", sa.Boolean(), None),
        ("employer_match_rate", sa.String(40), None),
        ("match_limit", sa.String(40), None),
        ("match_rule_notes", sa.Text(), None),
        ("vesting_enabled", sa.Boolean(), None),
        ("current_vested_percentage", sa.String(40), None),
        ("vesting_rule_notes", sa.Text(), None),
        ("status", sa.String(16), "'ACTIVE'"),
    )
    for name, column_type, server_default in columns:
        if name not in existing:
            op.add_column(
                "pension_plan_details",
                sa.Column(name, column_type, nullable=True, server_default=server_default),
            )
    op.execute(
        "UPDATE pension_plan_details SET product_type = pension_type WHERE product_type IS NULL"
    )


def downgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("pension_plan_details")
    }
    for name in (
        "status",
        "vesting_rule_notes",
        "current_vested_percentage",
        "vesting_enabled",
        "match_rule_notes",
        "match_limit",
        "employer_match_rate",
        "employer_match_enabled",
        "sponsor_balance",
        "participant_balance",
        "cnpb",
        "susep_process_number",
        "sponsor_cnpj",
        "sponsor_name",
        "closed_plan_modality",
        "product_type",
        "pension_system_type",
        "ownership_origin",
    ):
        if name in columns:
            op.drop_column("pension_plan_details", name)
