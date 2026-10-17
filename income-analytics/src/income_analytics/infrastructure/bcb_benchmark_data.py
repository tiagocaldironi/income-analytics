"""Central Bank of Brazil adapter for CDI and IPCA observations."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from income_analytics.application.benchmark_data import (
    BenchmarkDataUnavailable,
    BenchmarkNature,
    BenchmarkObservation,
)


class BcbBenchmarkDataProvider:
    _series: dict[str, tuple[int, BenchmarkNature]] = {
        "CDI": (12, "PERIODIC_RATE"),
        "IPCA": (433, "INFLATION_RATE"),
        # SGS 226 is TR (% p.m.) and 432 is the Selic target (% p.a.).
        "TR": (226, "PERIODIC_RATE"),
        "SELIC_TARGET": (432, "PERIODIC_RATE"),
    }

    def __init__(self, *, timeout_seconds: float = 15) -> None:
        self._timeout_seconds = timeout_seconds

    def observations(
        self, benchmark: str, *, start_date: date, end_date: date
    ) -> tuple[BenchmarkObservation, ...]:
        name = benchmark.upper()
        if name not in self._series:
            raise BenchmarkDataUnavailable(f"Benchmark automático indisponível: {name}.")
        series, nature = self._series[name]
        params = urlencode(
            {
                "formato": "json",
                "dataInicial": start_date.strftime("%d/%m/%Y"),
                "dataFinal": end_date.strftime("%d/%m/%Y"),
            }
        )
        try:
            with urlopen(
                f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados?{params}",
                timeout=self._timeout_seconds,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return tuple(
                BenchmarkObservation(
                    benchmark=name,
                    effective_date=datetime.strptime(item["data"], "%d/%m/%Y").date(),
                    value=Decimal(item["valor"].replace(",", ".")) / Decimal("100"),
                    nature=nature,
                    source="bcb",
                )
                for item in payload
            )
        except (KeyError, OSError, URLError, ValueError) as error:
            raise BenchmarkDataUnavailable(
                "Atualização automática de benchmark indisponível."
            ) from error
