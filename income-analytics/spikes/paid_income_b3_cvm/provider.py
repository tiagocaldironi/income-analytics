"""Evidence readers for official CVM files.

This module deliberately does not manufacture PaidIncomeEvent records from CVM
monthly FII reports: their public structured schema does not carry the payment
date or the amount paid per quota, both mandatory in the experimental contract.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from spikes.paid_income.models import ProviderResponse, QueryResult


@dataclass(frozen=True, slots=True)
class CvmFiiMonthlyEvidence:
    cnpj: str
    reference_date: date
    dividend_yield_month: Decimal | None
    amortization_month: Decimal | None


class CvmFiiMonthlyProvider:
    """Reads the official CVM INF_MENSAL FII CSV files downloaded for the spike."""

    provider_name = "cvm-inf-mensal-fii"

    def __init__(self, source_directory: Path) -> None:
        self._source_directory = source_directory

    def get_paid_income(
        self, ticker: str, start_date: date, end_date: date
    ) -> ProviderResponse:
        """Return a typed non-usable result instead of inventing payment events."""
        evidence = self.monthly_evidence(ticker, start_date, end_date)
        detail = (
            f"{len(evidence)} observações mensais de dividend yield encontradas; "
            "o esquema público CVM não contém data de pagamento nem valor por cota."
            if evidence
            else "Nenhuma observação CVM encontrada para o período."
        )
        return ProviderResponse(QueryResult.INVALID_PAYLOAD, None, 0, detail=detail)

    def monthly_evidence(
        self, ticker: str, start_date: date, end_date: date
    ) -> tuple[CvmFiiMonthlyEvidence, ...]:
        cnpj = FII_TICKER_CNPJ.get(ticker.upper())
        if cnpj is None:
            return ()
        records: list[CvmFiiMonthlyEvidence] = []
        for csv_path in sorted(
            self._source_directory.glob("*/inf_mensal_fii_complemento_*.csv")
        ):
            # Arquivos históricos da CVM contêm bytes Windows-1252; latin-1
            # preserva os nomes de colunas ASCII sem perder a leitura.
            with csv_path.open(encoding="latin-1", newline="") as source:
                for row in csv.DictReader(source, delimiter=";"):
                    if row.get("CNPJ_Fundo_Classe") != cnpj:
                        continue
                    reference = parse_iso_date(row.get("Data_Referencia"))
                    if reference is None or not start_date <= reference <= end_date:
                        continue
                    records.append(
                        CvmFiiMonthlyEvidence(
                            cnpj=cnpj,
                            reference_date=reference,
                            dividend_yield_month=parse_decimal(
                                row.get("Percentual_Dividend_Yield_Mes")
                            ),
                            amortization_month=parse_decimal(
                                row.get("Percentual_Amortizacao_Cotas_Mes")
                            ),
                        )
                    )
        return tuple(sorted(records, key=lambda item: item.reference_date))


# Mapping used only to prove the two FII test cases against their official CVM
# class CNPJ. It must not be confused with a production security master.
FII_TICKER_CNPJ = {
    "GGRC11": "26.614.291/0001-00",
    "HSML11": "32.892.018/0001-31",
}


def parse_iso_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value or "")
    except ValueError:
        return None


def parse_decimal(value: str | None) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None
