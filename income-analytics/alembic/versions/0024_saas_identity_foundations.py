"""Inert identity foundation; never claim existing portfolios or enable authentication."""

import sqlalchemy as sa

from alembic import op

revision = "0024_saas_identity_foundations"
down_revision = "0023_income_starter_guided_journey"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.CheckConstraint("status IN ('ACTIVE', 'SUSPENDED')", name="ck_users_status"),
    )
    op.create_table(
        "auth_identities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("issuer", sa.String(512), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.UniqueConstraint("issuer", "subject", name="uq_auth_identity_issuer_subject"),
    )
    # SQLite supports a nullable inline REFERENCES addition without rebuilding
    # the parent table and its existing financial foreign keys.
    op.execute("ALTER TABLE portfolios ADD COLUMN owner_user_id VARCHAR(36) REFERENCES users(id)")
    op.create_index("ix_portfolios_owner_user_id", "portfolios", ["owner_user_id"])


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT count(*) FROM users")).scalar_one():
        raise RuntimeError("Refusing to discard identities; restore a reviewed backup instead")
    # SQLite >=3.35 native DROP COLUMN avoids rebuilding the financial parent.
    op.drop_index("ix_portfolios_owner_user_id", table_name="portfolios")
    op.execute("ALTER TABLE portfolios DROP COLUMN owner_user_id")
    op.drop_table("auth_identities")
    op.drop_table("users")
