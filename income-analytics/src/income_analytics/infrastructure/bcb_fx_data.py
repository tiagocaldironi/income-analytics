"""BCB PTAX adapter. It returns normalized USD/BRL observations only."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.error import URLError
from urllib.request import urlopen

from income_analytics.application.fx_data import FxRateObservation, FxRateUnavailable


class BcbFxRateProvider:
    source = "bcb_ptax"

    def rate_on(
        self, base_currency: str, quote_currency: str, effective_date: date
    ) -> FxRateObservation:
        base, quote = base_currency.upper(), quote_currency.upper()
        if (base, quote) != ("USD", "BRL"):
            raise FxRateUnavailable(f"Câmbio automático indisponível para {base}/{quote}.")
        try:
            for offset in range(8):
                candidate_date = effective_date - timedelta(days=offset)
                formatted_date = candidate_date.strftime("%m-%d-%Y")
                url = (
                    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
                    "CotacaoDolarDia(dataCotacao=@dataCotacao)?"
                    f"@dataCotacao='{formatted_date}'&$format=json"
                )
                with urlopen(url, timeout=8) as response:  # noqa: S310 - fixed BCB URL
                    values = json.load(response).get("value", [])
                if values:
                    rate = Decimal(str(values[-1]["cotacaoVenda"]))
                    return FxRateObservation(
                        base_currency=base,
                        quote_currency=quote,
                        rate=rate,
                        effective_date=candidate_date,
                        source=self.source,
                    )
            raise FxRateUnavailable("BCB não publicou PTAX recente para esta moeda.")
        except (KeyError, ValueError, URLError, TimeoutError) as error:
            raise FxRateUnavailable("Não foi possível obter a PTAX agora.") from error

    def history(
        self, base_currency: str, quote_currency: str, start_date: date, end_date: date
    ) -> tuple[FxRateObservation, ...]:
        base, quote = base_currency.upper(), quote_currency.upper()
        if (base, quote) != ("USD", "BRL"):
            raise FxRateUnavailable(f"Câmbio automático indisponível para {base}/{quote}.")
        if end_date < start_date:
            return ()
        start = start_date.strftime("%m-%d-%Y")
        end = end_date.strftime("%m-%d-%Y")
        url = (
            "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
            "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?"
            f"@dataInicial='{start}'&@dataFinalCotacao='{end}'&$format=json&$top=10000"
        )
        try:
            with urlopen(url, timeout=30) as response:  # noqa: S310 - fixed BCB URL
                values = json.load(response).get("value", [])
            daily: dict[date, tuple[datetime, Decimal]] = {}
            for item in values:
                observed_at = datetime.fromisoformat(str(item["dataHoraCotacao"]))
                observation_date = observed_at.date()
                close = Decimal(str(item["cotacaoVenda"]))
                if observation_date not in daily or observed_at > daily[observation_date][0]:
                    daily[observation_date] = (observed_at, close)
            return tuple(
                FxRateObservation(
                    base_currency=base,
                    quote_currency=quote,
                    rate=value[1],
                    effective_date=day,
                    source=self.source,
                )
                for day, value in sorted(daily.items())
            )
        except (KeyError, ValueError, URLError, TimeoutError) as error:
            raise FxRateUnavailable("Não foi possível obter a série histórica PTAX.") from error
