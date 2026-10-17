from datetime import date
from decimal import Decimal
import base64
import json
from urllib.parse import unquote

from income_analytics.application.benchmark_data import BenchmarkDataUnavailable
from income_analytics.infrastructure import b3_benchmark_data as b3


class FakeResponse:
    body = b'{"results":[{"day":2,"rateValue1":"180.000,00"}]}'

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self.body


def test_b3_provider_queries_official_period_and_returns_normalized_observations(
    monkeypatch,
) -> None:
    requested = []

    def fake_urlopen(request, timeout):
        requested.append((request.full_url, timeout))
        return FakeResponse()

    monkeypatch.setattr(b3, "urlopen", fake_urlopen)
    result = b3.B3BenchmarkDataProvider().observations(
        "IBOV", start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)
    )

    assert len(requested) == 1
    assert "GetPortfolioDay" in requested[0][0]
    token = requested[0][0].rsplit("/", 1)[-1]
    payload = json.loads(base64.b64decode(unquote(token)))
    assert payload == {"index": "IBOVESPA", "year": 2026, "semester": 1, "language": "pt-br"}
    assert result[0].benchmark == "IBOV"
    assert result[0].value == Decimal("180000.00")


def test_b3_provider_reads_daily_observations_for_both_semesters(monkeypatch) -> None:
    requested = []

    def fake_urlopen(request, timeout):
        requested.append(request.full_url)
        response = FakeResponse()
        response.body = b'{"results":[{"day":2,"rateValue1":"180.000,00","rateValue7":"190.000,00"}]}'
        return response

    monkeypatch.setattr(b3, "urlopen", fake_urlopen)
    result = b3.B3BenchmarkDataProvider().observations(
        "IFIX", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)
    )

    assert len(requested) == 2
    assert [item.effective_date for item in result] == [date(2026, 1, 2), date(2026, 7, 2)]
    assert all(item.benchmark == "IFIX" and item.source == "b3" for item in result)


def test_b3_parser_rejects_unrecognized_official_table_format() -> None:
    try:
        b3.parse_b3_index_table(
            "<h4>IBOVESPA - 2026</h4><p>Formato inesperado</p>",
            benchmark="IBOV",
            year=2026,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )
    except BenchmarkDataUnavailable:
        pass
    else:
        raise AssertionError("tabela alterada deveria ser rejeitada")
