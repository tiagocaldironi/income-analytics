from datetime import date
from decimal import Decimal

from income_analytics.infrastructure import bcb_benchmark_data as bcb


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return b'[{"data":"02/01/2026","valor":"0,05"}]'


def test_bcb_adapter_converts_sgs_percent_to_daily_decimal(monkeypatch) -> None:
    def fake_urlopen(url, timeout):
        assert "bcdata.sgs.12" in url
        assert timeout == 15
        return FakeResponse()

    monkeypatch.setattr(bcb, "urlopen", fake_urlopen)
    result = bcb.BcbBenchmarkDataProvider().observations(
        "CDI", start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)
    )

    assert len(result) == 1
    assert result[0].effective_date == date(2026, 1, 2)
    assert result[0].value == Decimal("0.0005")
    assert result[0].nature == "PERIODIC_RATE"
