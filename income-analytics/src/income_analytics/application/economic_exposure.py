"""Optional, source-backed economic exposure classifications for portfolio assets."""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from income_analytics.application.income_starter import IncomeStarterError
from income_analytics.infrastructure.database import SessionFactory, initialize_database
from income_analytics.infrastructure.models import AssetEconomicExposureRecord, AssetRecord

ECONOMIC_CATEGORIES = {
    "BRAZIL_EQUITY",
    "INTERNATIONAL_EQUITY",
    "FIXED_INCOME",
    "LISTED_REAL_ESTATE",
    "DIRECT_REAL_ESTATE",
    "COMMODITIES",
    "CRYPTO",
    "CASH_EQUIVALENTS",
    "UNCLASSIFIED",
}


class EconomicExposureRepository:
    """Store only evidenced classifications; absence remains explicitly unknown."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionFactory,
        *,
        initialize=initialize_database,
    ) -> None:
        self._session_factory = session_factory
        self._initialize = initialize

    def get(self, asset_id: UUID) -> dict[str, Any]:
        self._initialize()
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(AssetEconomicExposureRecord)
                    .where(AssetEconomicExposureRecord.asset_id == str(asset_id))
                    .order_by(AssetEconomicExposureRecord.category)
                )
                .scalars()
                .all()
            )
            confirmed_count = sum(row.classification_status == "CONFIRMED" for row in rows)
            status = (
                "UNKNOWN"
                if confirmed_count == 0
                else "CLASSIFIED"
                if confirmed_count == len(rows)
                else "PARTIALLY_CLASSIFIED"
            )
            return {
                "asset_id": str(asset_id),
                "status": status,
                "exposures": [self._view(row) for row in rows],
            }

    def replace(self, asset_id: UUID, exposures: list[dict[str, Any]]) -> dict[str, Any]:
        if not exposures:
            raise IncomeStarterError("Informe pelo menos uma exposição ou UNCLASSIFIED.")
        if len(exposures) > 1 and any(item.get("exposure_share") is None for item in exposures):
            raise IncomeStarterError(
                "Informe as parcelas de todas as exposições para evitar dupla contagem."
            )
        parsed = []
        total = Decimal(0)
        for item in exposures:
            category = item.get("category")
            status = item.get("classification_status")
            share_value = item.get("exposure_share")
            if category not in ECONOMIC_CATEGORIES or status not in {"CONFIRMED", "UNKNOWN"}:
                raise IncomeStarterError("Categoria ou estado de classificação econômica inválido.")
            if status == "UNKNOWN":
                if category != "UNCLASSIFIED":
                    raise IncomeStarterError("Uma exposição desconhecida deve usar UNCLASSIFIED.")
                if share_value is not None:
                    try:
                        share = Decimal(str(share_value))
                    except (InvalidOperation, TypeError) as error:
                        raise IncomeStarterError(
                            "A parcela não classificada precisa de proporção válida."
                        ) from error
                    if not share.is_finite() or share <= 0 or share > 1:
                        raise IncomeStarterError(
                            "A parcela não classificada deve estar entre 0 e 100%."
                        )
                    total += share
                    item = {**item, "exposure_share": str(share)}
            else:
                if category == "UNCLASSIFIED":
                    raise IncomeStarterError(
                        "UNCLASSIFIED não pode ser registrado como confirmado."
                    )
                try:
                    share = Decimal(str(share_value))
                except (InvalidOperation, TypeError) as error:
                    raise IncomeStarterError(
                        "A exposição confirmada precisa de proporção válida."
                    ) from error
                if not share.is_finite() or share <= 0 or share > 1:
                    raise IncomeStarterError("A proporção deve estar entre 0 e 100%.")
                if not item.get("source") or not item.get("source_url", "").startswith("https://"):
                    raise IncomeStarterError("Classificação confirmada exige fonte documentada.")
                try:
                    reference_date = date.fromisoformat(str(item.get("source_reference_date")))
                except (ValueError, TypeError) as error:
                    raise IncomeStarterError(
                        "Informe a data de referência da classificação."
                    ) from error
                total += share
                item = {
                    **item,
                    "exposure_share": str(share),
                    "source_reference_date": reference_date,
                }
            parsed.append(item)
        if total and total != Decimal(1):
            raise IncomeStarterError(
                "As exposições devem somar 100%, incluindo a parte UNCLASSIFIED "
                "se houver parcela não conhecida."
            )
        if total == 0 and len(parsed) != 1:
            raise IncomeStarterError("Uma classificação UNKNOWN deve conter apenas UNCLASSIFIED.")
        self._initialize()
        with self._session_factory.begin() as session:
            if session.get(AssetRecord, str(asset_id)) is None:
                raise IncomeStarterError("Ativo não encontrado.")
            session.execute(
                delete(AssetEconomicExposureRecord).where(
                    AssetEconomicExposureRecord.asset_id == str(asset_id)
                )
            )
            for item in parsed:
                session.add(
                    AssetEconomicExposureRecord(
                        id=str(uuid4()),
                        asset_id=str(asset_id),
                        category=item["category"],
                        exposure_share=item.get("exposure_share"),
                        classification_status=item["classification_status"],
                        source=item.get("source"),
                        source_reference_date=item.get("source_reference_date"),
                        source_url=item.get("source_url"),
                        notes=item.get("notes"),
                    )
                )
        return self.get(asset_id)

    @staticmethod
    def _view(row: AssetEconomicExposureRecord) -> dict[str, Any]:
        return {
            "category": row.category,
            "exposure_share": row.exposure_share,
            "classification_status": row.classification_status,
            "source": row.source,
            "source_reference_date": row.source_reference_date.isoformat()
            if row.source_reference_date
            else None,
            "source_url": row.source_url,
            "notes": row.notes,
        }
