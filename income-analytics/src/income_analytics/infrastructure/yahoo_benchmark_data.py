"""Public market-index adapter for IBOV index-level observations."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from income_analytics.application.benchmark_data import (
    BenchmarkDataUnavailable,
    BenchmarkObservation,
)


class YahooBenchmarkDataProvider:
    def __init__(self, *, timeout_seconds: float = 5) -> None:
        self._timeout_seconds = timeout_seconds

    def observations(
        self, benchmark: str, *, start_date: date, end_date: date
    ) -> tuple[BenchmarkObservation, ...]:
        if benchmark.upper() != "IBOV":
            raise BenchmarkDataUnavailable("Benchmark automático indisponível.")
        start = datetime.combine(start_date - timedelta(days=7), datetime.min.time(), UTC)
        end = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), UTC)
        params = urlencode(
            {"period1": int(start.timestamp()), "period2": int(end.timestamp()), "interval": "1d"}
        )
        try:
            with urlopen(
                f"https://query1.finance.yahoo.com/v8/finance/chart/%5EBVSP?{params}",
                timeout=self._timeout_seconds,
            ) as response:
                result = json.loads(response.read().decode("utf-8"))["chart"]["result"][0]
            closes = result["indicators"]["quote"][0]["close"]
            return tuple(
                BenchmarkObservation(
                    benchmark="IBOV",
                    effective_date=datetime.fromtimestamp(timestamp, UTC).date(),
                    value=Decimal(str(close)),
                    nature="INDEX_LEVEL",
                    source="yahoo_finance",
                )
                for timestamp, close in zip(result["timestamp"], closes, strict=True)
                if close is not None
                and start_date <= datetime.fromtimestamp(timestamp, UTC).date() <= end_date
            )
        except (IndexError, KeyError, OSError, TypeError, URLError, ValueError) as error:
            raise BenchmarkDataUnavailable(
                "Atualização automática do IBOV indisponível."
            ) from error
