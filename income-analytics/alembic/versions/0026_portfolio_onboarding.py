"""Presentation-only onboarding metadata; no financial backfill."""

import sqlalchemy as sa

from alembic import op

revision = "0026_portfolio_onboarding"
down_revision = "0025_firebase_sessions_private"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "portfolio_onboarding",
        sa.Column("viewer_key", sa.String(36), primary_key=True),
        sa.Column(
            "portfolio_id",
            sa.String(36),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("current_step", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("updated_at", sa.Integer, nullable=False),
        sa.CheckConstraint("current_step BETWEEN 1 AND 4", name="ck_onboarding_step"),
        sa.CheckConstraint(
            "status IN ('ACTIVE','SKIPPED','COMPLETED')", name="ck_onboarding_status"
        ),
    )


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT COUNT(*) FROM portfolio_onboarding")).scalar():
        raise RuntimeError("Preserve onboarding metadata before downgrade")
    op.drop_table("portfolio_onboarding")
