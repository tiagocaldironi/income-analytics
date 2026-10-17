from __future__ import annotations

import csv
import io
import urllib.request
import zipfile
from datetime import date
from decimal import Decimal

from income_analytics.application.pension_market_data import PensionMarketDataUnavailable
from income_analytics.domain.pension_market_data import PensionFundQuota, PensionInvestmentVehicle


class CvmPensionMarketDataProvider:
    """Official CVM adapter; CSV/ZIP details never leave this boundary."""

    registration_url = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip"

    def resolve_vehicle(self, cnpj: str) -> PensionInvestmentVehicle:
        normalized = "".join(item for item in cnpj if item.isdigit())
        try:
            archive = zipfile.ZipFile(
                io.BytesIO(urllib.request.urlopen(self.registration_url, timeout=30).read())
            )
            rows = csv.DictReader(
                io.StringIO(archive.read("registro_classe.csv").decode("latin1")), delimiter=";"
            )
            for row in rows:
                if "".join(item for item in row["CNPJ_Classe"] if item.isdigit()) == normalized:
                    return PensionInvestmentVehicle(
                        pension_asset_id=__import__("uuid").uuid4(),
                        vehicle_name=row["Denominacao_Social"],
                        vehicle_cnpj=normalized,
                        vehicle_type="FUND_CLASS",
                        source="MANUAL_VALIDATION",
                    )
        except Exception as error:
            raise PensionMarketDataUnavailable("Cadastro CVM indisponível ou inválido.") from error
        raise PensionMarketDataUnavailable("Veículo não localizado no cadastro CVM.")

    def quota_history(
        self, vehicle: PensionInvestmentVehicle, start_date: date, end_date: date
    ) -> tuple[PensionFundQuota, ...]:
        result: list[PensionFundQuota] = []
        for year_month in {value.strftime("%Y%m") for value in (start_date, end_date)}:
            url = f"https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{year_month}.zip"
            try:
                archive = zipfile.ZipFile(
                    io.BytesIO(urllib.request.urlopen(url, timeout=30).read())
                )
                rows = csv.DictReader(
                    io.StringIO(archive.read(archive.namelist()[0]).decode("latin1")), delimiter=";"
                )
                for row in rows:
                    reference_date = date.fromisoformat(row["DT_COMPTC"])
                    cnpj = "".join(item for item in row["CNPJ_FUNDO_CLASSE"] if item.isdigit())
                    if (
                        cnpj == vehicle.vehicle_cnpj
                        and start_date <= reference_date <= end_date
                        and Decimal(row["VL_QUOTA"]) > 0
                    ):
                        result.append(
                            PensionFundQuota(
                                vehicle_id=vehicle.id,
                                reference_date=reference_date,
                                quota=Decimal(row["VL_QUOTA"]),
                            )
                        )
            except Exception as error:
                raise PensionMarketDataUnavailable(
                    "Informe Diário CVM indisponível ou inválido."
                ) from error
        return tuple(
            sorted(
                {item.reference_date: item for item in result}.values(),
                key=lambda item: item.reference_date,
            )
        )
