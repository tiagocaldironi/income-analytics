"""Session revocation, security audit and private metadata; no financial backfill."""

import sqlalchemy as sa

from alembic import op

revision = "0025_firebase_sessions_private"
down_revision = "0024_saas_identity_foundations"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "auth_identities",
        sa.Column("approved_methods", sa.Text, nullable=False, server_default="[]"),
    )
    op.add_column(
        "auth_identities",
        sa.Column("link_confirmed_until", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.Integer, nullable=False),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_table(
        "security_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36)),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("evidence_ref", sa.String(64)),
        sa.Column("resource_id", sa.String(36)),
        sa.Column("created_at", sa.Integer, nullable=False),
    )
    op.create_table(
        "security_rate_limits",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("window", sa.Integer, primary_key=True),
        sa.Column("count", sa.Integer, nullable=False),
    )
    op.create_table(
        "portfolio_asset_metadata",
        sa.Column("portfolio_id", sa.String(36), primary_key=True),
        sa.Column("asset_id", sa.String(36), primary_key=True),
        sa.Column("payload", sa.Text, nullable=False),
        sa.ForeignKeyConstraint(
            ["portfolio_id", "asset_id"],
            ["portfolio_assets.portfolio_id", "portfolio_assets.asset_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_table(
        "portfolio_market_prices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("portfolio_id", sa.String(36), nullable=False),
        sa.Column("asset_id", sa.String(36), nullable=False),
        sa.Column("price", sa.String(40), nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(80)),
        sa.Column("price_timestamp", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["portfolio_id", "asset_id"],
            ["portfolio_assets.portfolio_id", "portfolio_assets.asset_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_portfolio_market_prices_portfolio_id", "portfolio_market_prices", ["portfolio_id"]
    )


def downgrade():
    for table in (
        "auth_sessions",
        "security_audit",
        "portfolio_asset_metadata",
        "portfolio_market_prices",
    ):
        if op.get_bind().execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one():
            raise RuntimeError("Refusing to discard used SaaS data; review backup/restore first")
    for table in (
        "portfolio_market_prices",
        "portfolio_asset_metadata",
        "security_rate_limits",
        "security_audit",
        "auth_sessions",
    ):
        op.drop_table(table)

    op.execute("ALTER TABLE auth_identities DROP COLUMN link_confirmed_until")
    op.execute("ALTER TABLE auth_identities DROP COLUMN approved_methods")
