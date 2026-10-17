"""CVM capital-composition parser; it never guesses ticker/class mappings."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from io import TextIOWrapper
from zipfile import ZipFile

from income_analytics.application.issuer_market_cap import MarketDataStatus, ShareClassCapital
from income_analytics.infrastructure.cvm_fundamentals_data import CvmDataset


@dataclass(frozen=True, slots=True)
class CvmCapitalComposition:
    cnpj: str
    company_name: str
    reference_date: str
    ordinary_issued: Decimal
    preferred_issued: Decimal
    ordinary_treasury: Decimal
    preferred_treasury: Decimal
    source_reference: str


@dataclass(frozen=True, slots=True)
class SecurityClassMapping:
    issuer_id: str
    cnpj: str
    security_id: str
    ticker: str
    share_class: str
    shares_multiplier: Decimal | None
    source_reference: str


class CvmCapitalCompositionParser:
    """Read official DFP capital composition, retaining its source identity."""

    filename = "dfp_cia_aberta_composicao_capital_"
    required = {
        "CNPJ_CIA",
        "DT_REFER",
        "DENOM_CIA",
        "QT_ACAO_ORDIN_CAP_INTEGR",
        "QT_ACAO_PREF_CAP_INTEGR",
        "QT_ACAO_ORDIN_TESOURO",
        "QT_ACAO_PREF_TESOURO",
    }

    def parse(self, dataset: CvmDataset) -> tuple[CvmCapitalComposition, ...]:
        if dataset.statement_type != "DFP":
            raise ValueError("Composição de capital exige DFP oficial.")
        with ZipFile(__import__("io").BytesIO(dataset.payload)) as archive:
            name = next(
                (item for item in archive.namelist() if self.filename in item.casefold()), None
            )
            if name is None:
                raise ValueError("SOURCE_SCHEMA_ERROR: composição de capital ausente.")
            with archive.open(name) as raw:
                reader = csv.DictReader(TextIOWrapper(raw, encoding="latin-1"), delimiter=";")
                if not reader.fieldnames or not self.required.issubset(reader.fieldnames):
                    raise ValueError("SOURCE_SCHEMA_ERROR: colunas de capital ausentes.")
                return tuple(
                    CvmCapitalComposition(
                        row["CNPJ_CIA"],
                        row["DENOM_CIA"],
                        row["DT_REFER"],
                        self._decimal(row["QT_ACAO_ORDIN_CAP_INTEGR"]),
                        self._decimal(row["QT_ACAO_PREF_CAP_INTEGR"]),
                        self._decimal(row["QT_ACAO_ORDIN_TESOURO"]),
                        self._decimal(row["QT_ACAO_PREF_TESOURO"]),
                        f"{dataset.source_file}:{name}",
                    )
                    for row in reader
                )

    @staticmethod
    def _decimal(value: str) -> Decimal:
        try:
            return Decimal(value)
        except (InvalidOperation, TypeError) as error:
            raise ValueError("SOURCE_SCHEMA_ERROR: quantidade de ações inválida.") from error


class CvmCapitalStructureAdapter:
    """Convert explicit security mappings into auditable outstanding shares.

    The official CVM file has ON/PN quantities but no B3 ticker/security id and
    no universal quantity-scale metadata. Callers must provide both a class
    mapping and a source-backed multiplier; name matching is never used.
    """

    def normalize(
        self,
        *,
        composition: CvmCapitalComposition,
        mappings: tuple[SecurityClassMapping, ...],
        retrieved_at: datetime | None = None,
    ) -> tuple[ShareClassCapital, ...]:
        classes = {
            "ON": composition.ordinary_issued - composition.ordinary_treasury,
            "PN": composition.preferred_issued - composition.preferred_treasury,
        }
        relevant = tuple(mapping for mapping in mappings if mapping.cnpj == composition.cnpj)
        required_classes = {
            share_class for share_class, quantity in classes.items() if quantity > 0
        }
        if {mapping.share_class for mapping in relevant} != required_classes:
            raise ValueError("INSUFFICIENT_MARKET_DATA: mapeamento por classe incompleto.")
        if any(
            mapping.shares_multiplier is None or mapping.shares_multiplier <= 0
            for mapping in relevant
        ):
            raise ValueError("INSUFFICIENT_MARKET_DATA: unidade de ações não validada.")
        observed_at = retrieved_at or datetime.now(UTC)
        return tuple(
            ShareClassCapital(
                issuer_id=mapping.issuer_id,
                security_id=mapping.security_id,
                ticker=mapping.ticker,
                share_class=mapping.share_class,
                shares_outstanding=classes[mapping.share_class] * mapping.shares_multiplier,
                reference_date=__import__("datetime").date.fromisoformat(
                    composition.reference_date
                ),
                source="CVM_DFP_COMPOSICAO_CAPITAL",
                source_reference=f"{composition.source_reference};{mapping.source_reference}",
                retrieved_at=observed_at,
                status=MarketDataStatus.VALID,
            )
            for mapping in relevant
        )
