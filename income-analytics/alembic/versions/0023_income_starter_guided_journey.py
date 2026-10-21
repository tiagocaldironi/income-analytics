"""Separate the educational reserve journey from allocation models."""
# ruff: noqa: E501

import sqlalchemy as sa

from alembic import op

revision = "0023_income_starter_guided_journey"
down_revision = "0022_income_starter_review_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "income_starter_template_versions",
        sa.Column(
            "template_type", sa.String(length=24), nullable=False, server_default="ALLOCATION_MODEL"
        ),
    )
    with op.batch_alter_table("income_starter_template_versions") as batch_op:
        batch_op.create_check_constraint(
            "ck_income_starter_template_type",
            "template_type IN ('GUIDED_JOURNEY', 'ALLOCATION_MODEL')",
        )
    op.execute(
        sa.text(
            "UPDATE income_starter_template_versions SET template_type='GUIDED_JOURNEY', "
            "description='Jornada educacional para definir e acompanhar uma reserva de emergência, sem carteira-modelo.', "
            "objective='Ajudar a compreender, definir e acompanhar uma meta pessoal de reserva de emergência.', "
            "risk_profile='Jornada educacional; não representa perfil de risco', "
            "horizon='A meta depende das despesas essenciais e da necessidade individual de liquidez.', "
            "volatility_tolerance='A construção da reserva é um objetivo financeiro, não uma classificação de tolerância a risco.', "
            "typical_profile='Pessoa que deseja estruturar e acompanhar uma reserva de emergência.', "
            'characteristics_json=\'["Define a meta a partir de despesas essenciais e meses de cobertura ajustáveis.","O valor reservado é autodeclarado e não é certificado pelo motor financeiro.","Não presume que ativos da carteira tenham liquidez ou adequação para a reserva."]\', '
            'not_suitable_json=\'["Não substitui suitability, aconselhamento individual ou uma carteira de investimentos.","Pode não ser suficiente para necessidades financeiras complexas que exijam planejamento profissional."]\', '
            "methodology='Jornada educacional baseada na referência da CVM de 6 a 12 meses de despesas essenciais, ajustável pelo usuário. A faixa não é regra universal. Não recomenda ativos, não realiza suitability e não cria posições ou operações.' "
            "WHERE template_key='primeiros-passos'"
        )
    )
    op.create_table(
        "income_starter_journey_progress",
        sa.Column(
            "portfolio_id",
            sa.String(length=36),
            sa.ForeignKey("portfolios.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("essential_monthly_expenses", sa.String(length=40)),
        sa.Column("coverage_months", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("reserve_goal", sa.String(length=40)),
        sa.Column(
            "declared_reserved_amount", sa.String(length=40), nullable=False, server_default="0"
        ),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("coverage_months BETWEEN 1 AND 60", name="ck_reserve_coverage_months"),
        sa.CheckConstraint("current_step BETWEEN 1 AND 4", name="ck_reserve_current_step"),
    )
    op.create_table(
        "asset_economic_exposures",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "asset_id",
            sa.String(length=36),
            sa.ForeignKey("assets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("exposure_share", sa.String(length=40)),
        sa.Column("classification_status", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=80)),
        sa.Column("source_reference_date", sa.Date()),
        sa.Column("source_url", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint(
            "asset_id", "category", "source", name="uq_asset_economic_exposure_source"
        ),
        sa.CheckConstraint(
            "category IN ('BRAZIL_EQUITY','INTERNATIONAL_EQUITY','FIXED_INCOME','LISTED_REAL_ESTATE','DIRECT_REAL_ESTATE','COMMODITIES','CRYPTO','CASH_EQUIVALENTS','UNCLASSIFIED')",
            name="ck_economic_exposure_category",
        ),
        sa.CheckConstraint(
            "classification_status IN ('CONFIRMED','UNKNOWN')", name="ck_economic_exposure_status"
        ),
    )
    op.create_index(
        "ix_asset_economic_exposures_asset_id", "asset_economic_exposures", ["asset_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_asset_economic_exposures_asset_id", table_name="asset_economic_exposures")
    op.drop_table("asset_economic_exposures")
    op.drop_table("income_starter_journey_progress")
    with op.batch_alter_table("income_starter_template_versions") as batch_op:
        batch_op.drop_constraint("ck_income_starter_template_type", type_="check")
        batch_op.drop_column("template_type")
