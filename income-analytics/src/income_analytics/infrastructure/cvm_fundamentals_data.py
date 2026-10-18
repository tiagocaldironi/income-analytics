"""Raw CVM DFP/ITR ingestion; accounting decisions remain outside this adapter."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from io import TextIOWrapper
from zipfile import ZipFile

from income_analytics.application.cvm_magic_formula_normalization import CvmRawAccount


class CvmSourceSchemaError(ValueError):
    code = "SOURCE_SCHEMA_ERROR"


@dataclass(frozen=True, slots=True)
class CvmDataset:
    statement_type: str
    source_file: str
    retrieved_at: datetime
    payload: bytes


class CvmStatementParser:
    required = {
        "CD_CVM",
        "DT_REFER",
        "ORDEM_EXERC",
        "ESCALA_MOEDA",
        "CD_CONTA",
        "DS_CONTA",
        "VL_CONTA",
    }

    def parse(self, dataset: CvmDataset) -> tuple[CvmRawAccount, ...]:
        if dataset.statement_type not in {"DFP", "ITR"}:
            raise ValueError("Tipo de demonstração CVM inválido.")
        with ZipFile(__import__("io").BytesIO(dataset.payload)) as archive:
            records: list[CvmRawAccount] = []
            for name in archive.namelist():
                normalized_name = name.lower()
                if not normalized_name.endswith(".csv") or not any(
                    part in normalized_name for part in ("_dre_", "_bpa_", "_bpp_")
                ):
                    continue
                statement = (
                    "DRE"
                    if "_dre_" in normalized_name
                    else "BPA"
                    if "_bpa_" in normalized_name
                    else "BPP"
                )
                with archive.open(name) as raw:
                    reader = csv.DictReader(TextIOWrapper(raw, encoding="latin-1"), delimiter=";")
                    if not reader.fieldnames or not self.required.issubset(reader.fieldnames):
                        raise CvmSourceSchemaError(f"{self.code}: colunas ausentes em {name}.")
                    for row in reader:
                        if row.get("ORDEM_EXERC") != "ÚLTIMO":
                            continue
                        value = self._decimal(row["VL_CONTA"])
                        if value is None:
                            continue
                        scope = "CONSOLIDATED" if "_con_" in normalized_name else "INDIVIDUAL"
                        records.append(
                            CvmRawAccount(
                                str(row["CD_CVM"]),
                                str(row["CD_CVM"]),
                                row["DT_REFER"],
                                dataset.statement_type,
                                scope,
                                statement,
                                row["CD_CONTA"],
                                row["DS_CONTA"],
                                value,
                                dataset.source_file,
                                row.get("DT_INI_EXERC") or None,
                                row.get("DT_FIM_EXERC") or row["DT_REFER"],
                                "BRL",
                                row["ESCALA_MOEDA"],
                                row.get("VERSAO"),
                            )
                        )
            return tuple(records)

    @staticmethod
    def _decimal(value: str) -> Decimal | None:
        try:
            return Decimal(value.replace(",", "."))
        except AttributeError, InvalidOperation:
            return None


class CvmDatasetDownloader:
    """Build official annual dataset URLs without embedding accounting logic."""

    base_url = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"

    def url(self, statement_type: str, year: int) -> str:
        kind = statement_type.upper()
        if kind not in {"DFP", "ITR"}:
            raise ValueError("Dataset CVM deve ser DFP ou ITR.")
        return f"{self.base_url}/{kind}/DADOS/{kind.casefold()}_cia_aberta_{year}.zip"

    def dataset(self, statement_type: str, source_file: str, payload: bytes) -> CvmDataset:
        return CvmDataset(statement_type.upper(), source_file, datetime.now(UTC), payload)
