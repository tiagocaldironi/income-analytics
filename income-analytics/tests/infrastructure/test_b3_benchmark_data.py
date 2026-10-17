from datetime import date
from decimal import Decimal

from income_analytics.application.benchmark_data import BenchmarkDataUnavailable
from income_analytics.infrastructure import b3_benchmark_data as b3


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return b"""<h4>IBOVESPA - 2026</h4><table>
        <tr><th>Dia</th><th>Jan</th><th>Fev</th><th>Mar</th><th>Abr</th><th>Mai</th><th>Jun</th></tr>
        <tr><td>2</td><td>180.000,00</td><td></td><td></td><td></td><td></td><td></td></tr>
        </table>"""


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
    assert "IBOVESPA" in requested[0][0]
    assert "year=2026" in requested[0][0]
    assert "semester=1" in requested[0][0]
    assert result[0].benchmark == "IBOV"
    assert result[0].value == Decimal("180000.00")


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
