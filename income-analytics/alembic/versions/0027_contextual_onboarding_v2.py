"""Isolated user preferences, journey progress and minimal product events."""
import sqlalchemy as sa
from alembic import op
revision="0027_contextual_onboarding_v2"
down_revision="0026_portfolio_onboarding"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("onboarding_preferences_v2",sa.Column("viewer_key",sa.String(36),primary_key=True),sa.Column("owner_user_id",sa.String(36),sa.ForeignKey("users.id")),sa.Column("intent",sa.String(24)),sa.Column("chosen_at",sa.Integer),sa.Column("deferred_at",sa.Integer),sa.Column("version",sa.Integer,nullable=False,server_default="2"))
    op.create_table("onboarding_journeys_v2",sa.Column("viewer_key",sa.String(36),primary_key=True),sa.Column("portfolio_id",sa.String(36),sa.ForeignKey("portfolios.id",ondelete="CASCADE"),primary_key=True),sa.Column("owner_user_id",sa.String(36),sa.ForeignKey("users.id")),sa.Column("version",sa.Integer,nullable=False,server_default="2"),sa.Column("status",sa.String(16),nullable=False,server_default="ACTIVE"),sa.Column("last_step",sa.Integer,nullable=False,server_default="1"),sa.Column("selected_class",sa.String(32)),sa.Column("first_asset_at",sa.Integer),sa.Column("analysis_at",sa.Integer),sa.Column("completed_at",sa.Integer),sa.Column("dismissed_at",sa.Integer),sa.Column("updated_at",sa.Integer,nullable=False),sa.CheckConstraint("status IN ('ACTIVE','SKIPPED','DISMISSED','COMPLETED')",name="ck_onboarding_v2_status"),sa.CheckConstraint("last_step BETWEEN 1 AND 6",name="ck_onboarding_v2_step"))
    op.create_table("onboarding_events_v2",sa.Column("viewer_key",sa.String(36),primary_key=True),sa.Column("portfolio_id",sa.String(36),sa.ForeignKey("portfolios.id",ondelete="CASCADE"),primary_key=True),sa.Column("version",sa.Integer,primary_key=True,server_default="2"),sa.Column("event_name",sa.String(48),primary_key=True),sa.Column("occurred_at",sa.Integer,nullable=False))

    # Respect prior skip/completion decisions without inventing new achievements.
    op.execute(sa.text("INSERT INTO onboarding_journeys_v2 (viewer_key,portfolio_id,owner_user_id,version,status,last_step,updated_at) SELECT viewer_key,portfolio_id,CASE WHEN viewer_key='local' THEN NULL ELSE viewer_key END,2,status,2,updated_at FROM portfolio_onboarding WHERE status IN ('SKIPPED','COMPLETED')"))

def downgrade():
    for name in ("onboarding_events_v2","onboarding_journeys_v2","onboarding_preferences_v2"):
        if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM "+name)).scalar():
            raise RuntimeError("Preserve contextual onboarding data before downgrade")
    for name in ("onboarding_events_v2","onboarding_journeys_v2","onboarding_preferences_v2"): op.drop_table(name)
