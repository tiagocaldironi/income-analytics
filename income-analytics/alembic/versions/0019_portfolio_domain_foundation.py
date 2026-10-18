"""Add explicit MAIN_PORTFOLIO ownership to private portfolio data."""

import sqlalchemy as sa

from alembic import op

revision = "0019_portfolio_domain_foundation"
down_revision = "0018_portfolio_price_refresh_runs"
branch_labels = None
depends_on = None

MAIN_ID = "7a54eeb7-542a-5832-8544-8be7dcb0237e"
OWNED = (
    "fixed_income_details",
    "pension_plan_details",
    "pension_investment_vehicles",
    "real_estate_details",
    "recurring_rules",
    "financial_events",
    "portfolio_configuration",
    "allocation_targets",
    "asset_targets",
    "imported_paid_income",
    "b3_import_batches",
    "b3_imported_records",
    "portfolio_dashboard_snapshot",
    "market_price_refresh_runs",
)


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "portfolios",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    now = "2026-10-18T00:00:00+00:00"
    currency = (
        bind.execute(
            sa.text("SELECT value FROM portfolio_configuration WHERE key='portfolio_base_currency'")
        ).scalar()
        or "BRL"
    )
    bind.execute(
        sa.text(
            "INSERT INTO portfolios(id,name,base_currency,status,created_at,updated_at) "
            "VALUES (:id,'Minha Carteira',:currency,'ACTIVE',:now,:now)"
        ),
        {"id": MAIN_ID, "currency": currency, "now": now},
    )
    op.create_table(
        "portfolio_assets",
        sa.Column(
            "portfolio_id",
            sa.String(36),
            sa.ForeignKey("portfolios.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "asset_id",
            sa.String(36),
            sa.ForeignKey("assets.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )
    bind.execute(
        sa.text("INSERT INTO portfolio_assets(portfolio_id,asset_id) SELECT :id,id FROM assets"),
        {"id": MAIN_ID},
    )

    for table in OWNED:
        op.add_column(table, sa.Column("portfolio_id", sa.String(36), nullable=True))
        bind.execute(
            sa.text(f"UPDATE {table} SET portfolio_id=:id WHERE portfolio_id IS NULL"),
            {"id": MAIN_ID},
        )
        with op.batch_alter_table(table) as batch:
            batch.alter_column("portfolio_id", existing_type=sa.String(36), nullable=False)
            batch.create_foreign_key(
                f"fk_{table}_portfolio_id_portfolios",
                "portfolios",
                ["portfolio_id"],
                ["id"],
                ondelete="RESTRICT",
            )
            batch.create_index(f"ix_{table}_portfolio_id", ["portfolio_id"])

    # These tables are keyed by configuration value inside a portfolio.
    for table, columns in (
        ("portfolio_configuration", ("portfolio_id", "key")),
        ("allocation_targets", ("portfolio_id", "asset_class")),
        ("asset_targets", ("portfolio_id", "asset_id")),
        ("fixed_income_details", ("portfolio_id", "asset_id")),
        ("pension_plan_details", ("portfolio_id", "asset_id")),
        ("real_estate_details", ("portfolio_id", "asset_id")),
    ):
        with op.batch_alter_table(
            table, recreate="always", naming_convention={"pk": f"pk_{table}"}
        ) as batch:
            batch.drop_constraint(f"pk_{table}", type_="primary")
            batch.create_primary_key(f"pk_{table}", list(columns))

    # Keep deduplication local to the portfolio for import and income records.
    with op.batch_alter_table(
        "imported_paid_income",
        recreate="always",
        naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"},
    ) as batch:
        batch.drop_constraint("uq_imported_paid_income_raw_fingerprint", type_="unique")
        batch.create_unique_constraint(
            "uq_paid_income_portfolio_fingerprint", ["portfolio_id", "raw_fingerprint"]
        )
    with op.batch_alter_table("b3_imported_records", recreate="always") as batch:
        batch.drop_constraint("uq_b3_imported_record_identity", type_="unique")
        batch.create_unique_constraint(
            "uq_b3_imported_record_identity",
            ["portfolio_id", "source", "fingerprint", "occurrence_index"],
        )
    op.create_index(
        "ux_dashboard_snapshot_portfolio",
        "portfolio_dashboard_snapshot",
        ["portfolio_id"],
        unique=True,
    )

    # B3 audit rows can outlive manually deleted events. Keep the raw imported
    # row and clear only its stale optional link before enforcing scoped FKs.
    bind.execute(
        sa.text(
            "UPDATE b3_imported_records SET financial_event_id=NULL "
            "WHERE financial_event_id IS NOT NULL AND NOT EXISTS "
            "(SELECT 1 FROM financial_events e WHERE e.id=b3_imported_records.financial_event_id)"
        )
    )

    for table, asset_column in (
        ("fixed_income_details", "asset_id"),
        ("pension_plan_details", "asset_id"),
        ("pension_investment_vehicles", "pension_asset_id"),
        ("real_estate_details", "asset_id"),
        ("recurring_rules", "asset_id"),
        ("asset_targets", "asset_id"),
        ("financial_events", "asset_id"),
        ("imported_paid_income", "asset_id"),
        ("b3_imported_records", "asset_id"),
    ):
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.create_foreign_key(
                f"fk_{table}_portfolio_asset",
                "portfolio_assets",
                ["portfolio_id", asset_column],
                ["portfolio_id", "asset_id"],
                ondelete="RESTRICT",
            )

    with op.batch_alter_table("financial_events", recreate="always") as batch:
        batch.create_unique_constraint("uq_financial_events_portfolio_id", ["portfolio_id", "id"])
    with op.batch_alter_table("b3_import_batches", recreate="always") as batch:
        batch.create_unique_constraint("uq_b3_batches_portfolio_id", ["portfolio_id", "id"])
    for table, column, target in (
        ("imported_paid_income", "financial_event_id", "financial_events"),
        ("b3_imported_records", "financial_event_id", "financial_events"),
        ("b3_imported_records", "batch_id", "b3_import_batches"),
    ):
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.create_foreign_key(
                f"fk_{table}_portfolio_{column}",
                target,
                ["portfolio_id", column],
                ["portfolio_id", "id"],
                ondelete="RESTRICT",
            )


def downgrade() -> None:
    raise RuntimeError(
        "Portfolio ownership migration is intentionally irreversible; "
        "restore the verified pre-migration backup."
    )
