"""Extensible registry and read contracts for market opportunity tools."""

from dataclasses import asdict, dataclass
from enum import StrEnum


class ToolCategory(StrEnum):
    OPPORTUNITY_DISCOVERY = "OPPORTUNITY_DISCOVERY"
    ANALYSIS = "ANALYSIS"
    INCOME = "INCOME"
    VALUATION = "VALUATION"
    PLANNING = "PLANNING"


class ToolDataStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    DATA_GAP = "DATA_GAP"
    VALIDATION_REQUIRED = "VALIDATION_REQUIRED"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class InvestmentToolDefinition:
    id: str
    slug: str
    name: str
    description: str
    category: ToolCategory
    route: str
    status: ToolDataStatus
    icon: str
    version: str

    def serialize(self) -> dict[str, str]:
        payload = asdict(self)
        payload["category"] = self.category.value
        payload["status"] = self.status.value
        return payload


TOOLS = (
    InvestmentToolDefinition(
        id="MAGIC_FORMULA_STOCKS",
        slug="magic-formula-stocks",
        name="Fórmula Mágica — Ações",
        description="Ranking de empresas que combina qualidade operacional e preço.",
        category=ToolCategory.OPPORTUNITY_DISCOVERY,
        route="tools-magic-formula-stocks",
        status=ToolDataStatus.VALIDATION_REQUIRED,
        icon="◈",
        version="MAGIC_FORMULA_STOCKS_V1",
    ),
    InvestmentToolDefinition(
        id="MAGIC_FORMULA_FIIS",
        slug="magic-formula-fiis",
        name="Fórmula Mágica — FIIs",
        description=(
            "Ranking de fundos imobiliários que combina atratividade e qualidade sustentável."
        ),
        category=ToolCategory.OPPORTUNITY_DISCOVERY,
        route="tools-magic-formula-fiis",
        status=ToolDataStatus.DATA_GAP,
        icon="▦",
        version="MF_FII_V3",
    ),
)


def ranking_contract(tool: InvestmentToolDefinition) -> dict[str, object]:
    return {
        "tool": tool.id,
        "methodology_version": tool.version,
        "reference_date": None,
        "universe": [],
        "filters": {},
        "items": [],
        "data_status": tool.status.value,
        "message": (
            "Dados fundamentais ainda não estão disponíveis de forma confiável para este ranking."
        ),
    }
