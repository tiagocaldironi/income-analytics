"""Create the versioned Income Starter catalog in draft-only state."""

# Editorial copy is stored verbatim here; long content strings are intentionally not reflowed.
# ruff: noqa: E501

import json
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "0021_income_starter_draft_catalog"
down_revision = "0020_shared_pension_quota_identity"
branch_labels = None
depends_on = None

METHODOLOGY_SOURCES = [
    {
        "type": "CONCEPTUAL",
        "title": "Asset Allocation and Diversification",
        "organization": "Investor.gov / U.S. Securities and Exchange Commission",
        "url": "https://www.investor.gov/introduction-investing/getting-started/asset-allocation",
        "supports": "Conceitos de alocação, horizonte, tolerância a risco e diversificação; não documenta percentuais para estes modelos.",
    },
    {
        "type": "REGULATORY_REFERENCE",
        "title": "Resolução CVM 30 (texto consolidado)",
        "organization": "Comissão de Valores Mobiliários",
        "url": "https://conteudo.cvm.gov.br/legislacao/resolucoes/resol030.html",
        "supports": "Referência para análise regulatória de adequação ao perfil; não valida estes modelos ou percentuais.",
    },
]

MODELS = [
    {
        "key": "primeiros-passos",
        "name": "Primeiros Passos",
        "description": "Uma proposta educacional ainda em elaboração, voltada à simplicidade e à compreensão de liquidez e preservação de recursos.",
        "objective": "Apresentar uma abordagem inicial com prioridade conceitual para liquidez, simplicidade e preservação de recursos.",
        "risk": "Baixa exposição a oscilações (descrição conceitual, em revisão)",
        "horizon": "A definir conforme objetivo e necessidade de liquidez; não é uma recomendação de prazo.",
        "tolerance": "Voltado conceitualmente a quem prefere compreender e controlar oscilações; não equivale a avaliação individual de perfil.",
        "knowledge": "Conhecimento inicial; a pessoa deve compreender liquidez, risco de crédito, prazo e possibilidade de perda.",
        "profile": "Pessoa começando a investir, aprendendo sobre risco e liquidez, que pode ainda estar construindo sua reserva de emergência.",
        "characteristics": [
            "Baixa complexidade como objetivo editorial.",
            "Atenção a acesso aos recursos e preservação.",
            "A reserva de emergência é uma necessidade financeira específica, não sinônimo de perfil conservador.",
        ],
        "not_suitable": [
            "Pode não fazer sentido para objetivos de longo prazo que demandem maior diversificação e para quem aceite volatilidade após atender às necessidades de liquidez."
        ],
    },
    {
        "key": "conservadora",
        "name": "Conservadora",
        "description": "Uma proposta educacional em elaboração para priorizar estabilidade e previsibilidade, sujeita à revisão de sua metodologia.",
        "objective": "Priorizar estabilidade patrimonial e previsibilidade, com diversificação a ser definida por metodologia validada.",
        "risk": "Baixa tolerância a perdas (descrição conceitual, em revisão)",
        "horizon": "A definir conforme objetivos, prazos e liquidez necessários.",
        "tolerance": "Conceitualmente orientada a pessoas com baixa disposição para oscilações e perdas temporárias.",
        "knowledge": "É necessário compreender que renda fixa também envolve riscos de crédito, mercado, inflação e liquidez.",
        "profile": "Investidor que prioriza estabilidade e previsibilidade e demonstra baixa tolerância a perdas.",
        "characteristics": [
            "A metodologia avaliará instrumentos e riscos de renda fixa.",
            "Liquidez, crédito, inflação e vencimentos precisam ser considerados.",
        ],
        "not_suitable": [
            "Pode não fazer sentido para quem aceita oscilações significativas e busca maior exposição ao crescimento de longo prazo."
        ],
    },
    {
        "key": "moderada",
        "name": "Moderada",
        "description": "Uma proposta educacional em elaboração para equilibrar estabilidade e crescimento, ainda sem distribuição definida.",
        "objective": "Equilibrar estabilidade e potencial de crescimento, após validação da metodologia e das alocações.",
        "risk": "Tolerância intermediária a oscilações (descrição conceitual, em revisão)",
        "horizon": "Associado conceitualmente a objetivos de médio ou longo prazo; requer validação por objetivo.",
        "tolerance": "Pressupõe disposição para suportar oscilações temporárias, sem inferir adequação individual.",
        "knowledge": "Compreensão básica de diversificação, risco de mercado, liquidez e perdas temporárias.",
        "profile": "Pessoa com reserva financeira constituída, horizonte de médio ou longo prazo e disposição para suportar oscilações temporárias.",
        "characteristics": [
            "A proposta metodológica avaliará combinação entre classes.",
            "Diversificação e eventual exposição internacional dependem de validação.",
        ],
        "not_suitable": [
            "Pode não fazer sentido para quem usará parcela relevante do patrimônio em prazo curto ou não tolera perdas temporárias."
        ],
    },
    {
        "key": "arrojada",
        "name": "Arrojada",
        "description": "Uma proposta educacional em elaboração para objetivos de crescimento de longo prazo e aceitação de maior volatilidade.",
        "objective": "Priorizar crescimento patrimonial no longo prazo, sujeito à validação financeira e regulatória.",
        "risk": "Maior tolerância a oscilações (descrição conceitual, em revisão)",
        "horizon": "Longo prazo como característica conceitual; prazos concretos dependem de homologação.",
        "tolerance": "Pressupõe capacidade e disposição para suportar volatilidade e perdas expressivas.",
        "knowledge": "Conhecimento dos riscos de mercado e de concentração em classes voláteis.",
        "profile": "Investidor com horizonte longo, capacidade financeira para suportar perdas e conhecimento dos riscos de renda variável.",
        "characteristics": [
            "A proposta avaliará diversificação nacional e internacional.",
            "Qualquer parcela de renda fixa e percentuais dependem de metodologia aprovada.",
        ],
        "not_suitable": [
            "Pode não fazer sentido para quem tem baixa tolerância a perdas, necessidade imediata de liquidez ou objetivos de curto prazo."
        ],
    },
]


def upgrade() -> None:
    op.create_table(
        "income_starter_template_versions",
        sa.Column("id", sa.String(120), primary_key=True),
        sa.Column("template_key", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("risk_profile", sa.String(80), nullable=False),
        sa.Column("horizon", sa.String(120), nullable=False),
        sa.Column("volatility_tolerance", sa.Text(), nullable=False),
        sa.Column("knowledge", sa.Text(), nullable=False),
        sa.Column("typical_profile", sa.Text(), nullable=False),
        sa.Column("characteristics_json", sa.Text(), nullable=False),
        sa.Column("not_suitable_json", sa.Text(), nullable=False),
        sa.Column("author", sa.String(120), nullable=False),
        sa.Column("methodology", sa.Text(), nullable=False),
        sa.Column("methodology_sources_json", sa.Text(), nullable=False),
        sa.Column("allocation_sources_json", sa.Text(), nullable=False),
        sa.Column("allocations_json", sa.Text()),
        sa.Column("allocations_validated", sa.Boolean(), nullable=False),
        sa.Column("financial_review_status", sa.String(16), nullable=False),
        sa.Column("regulatory_review_status", sa.String(16), nullable=False),
        sa.Column("reviewed_by", sa.String(120)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("template_key", "version", name="uq_income_starter_version"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'IN_REVIEW', 'PUBLISHED')", name="ck_income_starter_status"
        ),
    )
    op.create_index(
        "ix_income_starter_template_key", "income_starter_template_versions", ["template_key"]
    )
    op.create_table(
        "portfolio_strategy_metadata",
        sa.Column(
            "portfolio_id",
            sa.String(36),
            sa.ForeignKey("portfolios.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("strategy_name", sa.String(120), nullable=False),
        sa.Column("template_key", sa.String(64)),
        sa.Column("template_version", sa.Integer()),
        sa.Column("customized", sa.Boolean(), nullable=False),
        sa.Column("adopted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_allocations_json", sa.Text(), nullable=False),
    )

    now = datetime.now(UTC).isoformat()
    bind = op.get_bind()
    for model in MODELS:
        bind.execute(
            sa.text(
                "INSERT INTO income_starter_template_versions "
                "(id, template_key, version, name, status, description, objective, risk_profile, "
                "horizon, volatility_tolerance, knowledge, typical_profile, characteristics_json, "
                "not_suitable_json, author, methodology, methodology_sources_json, "
                "allocation_sources_json, allocations_json, allocations_validated, "
                "financial_review_status, regulatory_review_status, reviewed_by, reviewed_at, "
                "created_at, published_at) VALUES (:id,:key,1,:name,'DRAFT',:description,:objective,"
                ":risk,:horizon,:tolerance,:knowledge,:profile,:characteristics,:not_suitable,"
                ":author,:methodology,:sources,'[]',NULL,0,'PENDING','PENDING',NULL,NULL,:now,NULL)"
            ),
            {
                "id": f"{model['key']}@1",
                "key": model["key"],
                "name": model["name"],
                "description": model["description"],
                "objective": model["objective"],
                "risk": model["risk"],
                "horizon": model["horizon"],
                "tolerance": model["tolerance"],
                "knowledge": model["knowledge"],
                "profile": model["profile"],
                "characteristics": json.dumps(model["characteristics"], ensure_ascii=False),
                "not_suitable": json.dumps(model["not_suitable"], ensure_ascii=False),
                "author": "Income Analytics — equipe editorial; revisão pendente",
                "methodology": (
                    "Rascunho editorial baseado em conceitos de alocação, diversificação, horizonte e risco. "
                    "Nenhuma distribuição ou percentual foi definido. As fontes conceituais não comprovam "
                    "percentuais. Metodologia de alocação, fontes de alocação e adaptações Income dependem "
                    "de documentação e revisão financeira e regulatória antes da publicação."
                ),
                "sources": json.dumps(METHODOLOGY_SOURCES, ensure_ascii=False),
                "now": now,
            },
        )


def downgrade() -> None:
    op.drop_table("portfolio_strategy_metadata")
    op.drop_index("ix_income_starter_template_key", table_name="income_starter_template_versions")
    op.drop_table("income_starter_template_versions")
