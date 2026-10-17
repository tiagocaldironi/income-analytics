import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from income_analytics.application.market_data import MarketDataUnavailable
from income_analytics.infrastructure.b3_cotahist_market_data import (
    B3CotahistMarketDataProvider,
)


def _quote_record(*, quote_date: str, ticker: str, close_cents: int) -> bytes:
    record = bytearray(b" " * 245)
    record[0:2] = b"01"
    record[2:10] = quote_date.encode("ascii")
    record[12:24] = ticker.encode("ascii").ljust(12, b" ")
    record[108:121] = str(close_cents).encode("ascii").rjust(13, b"0")
    return bytes(record) + b"\n"


def test_cotahist_returns_last_valid_close_before_requested_date(tmp_path) -> None:
    archive_path = tmp_path / "COTAHIST_A2025.ZIP"
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "COTAHIST_A2025.TXT",
            _quote_record(quote_date="20250515", ticker="SAPR11", close_cents=3012)
            + _quote_record(quote_date="20250516", ticker="SAPR11", close_cents=3063),
        )

    observation = B3CotahistMarketDataProvider(cache_directory=tmp_path).price_on(
        "SAPR11", date(2025, 5, 17)
    )

    assert observation.source == "b3_cotahist"
    assert observation.effective_date == date(2025, 5, 16)
    assert observation.price == Decimal("30.63")
    assert observation.currency_code == "BRL"


def test_cotahist_market_evidence_has_deterministic_raw_record_reference(tmp_path) -> None:
    archive_path = tmp_path / "COTAHIST_A2025.ZIP"
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "COTAHIST_A2025.TXT",
            _quote_record(quote_date="20251230", ticker="WEGE3", close_cents=4851),
        )

    evidence = B3CotahistMarketDataProvider(cache_directory=tmp_path).price_evidence_on(
        "WEGE3", date(2025, 12, 31)
    )

    assert evidence.price == Decimal("48.51")
    assert evidence.effective_date == date(2025, 12, 30)
    assert evidence.source_file == "COTAHIST_A2025.ZIP"
    assert evidence.record_reference == (
        "COTAHIST_A2025.ZIP|COTAHIST_A2025.TXT|line=1|date=20251230|ticker=WEGE3|close=48.51"
    )


def test_cotahist_history_many_scans_multiple_symbols_and_keeps_daily_source(tmp_path) -> None:
    archive_path = tmp_path / "COTAHIST_A2025.ZIP"
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "COTAHIST_A2025.TXT",
            _quote_record(quote_date="20250515", ticker="WEGE3", close_cents=4851)
            + _quote_record(quote_date="20250515", ticker="ITSA4", close_cents=1032)
            + _quote_record(quote_date="20250515", ticker="OUTRO3", close_cents=100),
        )

    series = B3CotahistMarketDataProvider(cache_directory=tmp_path).history_many(
        {"WEGE3", "ITSA4"}, start_date=date(2025, 1, 1), end_date=date(2025, 12, 31)
    )

    assert set(series) == {"WEGE3", "ITSA4"}
    assert series["WEGE3"][0].source == "b3_cotahist"
    assert series["WEGE3"][0].price == Decimal("48.51")
    assert series["ITSA4"][0].price == Decimal("10.32")


def test_current_annual_archive_is_refreshed_when_cache_is_stale(tmp_path, monkeypatch) -> None:
    today = date.today()
    archive_path = tmp_path / f"COTAHIST_A{today.year}.ZIP"
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            f"COTAHIST_A{today.year}.TXT",
            _quote_record(
                quote_date=(today - timedelta(days=10)).strftime("%Y%m%d"),
                ticker="WEGE3",
                close_cents=4800,
            ),
        )
    stale_time = (datetime.now() - timedelta(days=2)).timestamp()
    archive_path.touch()
    os.utime(archive_path, (stale_time, stale_time))
    provider = B3CotahistMarketDataProvider(cache_directory=tmp_path)
    refreshed = []

    def download(_url: str, destination: Path) -> None:
        refreshed.append(destination)
        with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
            archive.writestr(
                f"COTAHIST_A{today.year}.TXT",
                _quote_record(
                    quote_date=(today - timedelta(days=1)).strftime("%Y%m%d"),
                    ticker="WEGE3",
                    close_cents=4900,
                ),
            )

    monkeypatch.setattr(provider, "_download", download)

    observation = provider.latest_price("WEGE3")

    assert refreshed == [archive_path]
    assert observation.effective_date == today - timedelta(days=1)
    assert observation.price == Decimal("49")


def test_failed_current_archive_refresh_keeps_usable_cached_quote(tmp_path, monkeypatch) -> None:
    today = date.today()
    archive_path = tmp_path / f"COTAHIST_A{today.year}.ZIP"
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            f"COTAHIST_A{today.year}.TXT",
            _quote_record(
                quote_date=(today - timedelta(days=1)).strftime("%Y%m%d"),
                ticker="WEGE3",
                close_cents=4800,
            ),
        )
    stale_time = (datetime.now() - timedelta(days=2)).timestamp()
    archive_path.touch()
    os.utime(archive_path, (stale_time, stale_time))
    provider = B3CotahistMarketDataProvider(cache_directory=tmp_path)
    attempts = []

    def fail_download(_url: str, _destination: Path) -> None:
        attempts.append(True)
        raise MarketDataUnavailable("B3 temporariamente indisponível")

    monkeypatch.setattr(provider, "_download", fail_download)

    observation = provider.latest_price("WEGE3")
    provider.latest_price("WEGE3")

    assert observation.effective_date == today - timedelta(days=1)
    assert observation.price == Decimal("48")
    assert archive_path.exists()
    assert len(attempts) == 1


def test_missing_quote_reports_failed_stale_archive_refresh(tmp_path, monkeypatch) -> None:
    today = date.today()
    archive_path = tmp_path / f"COTAHIST_A{today.year}.ZIP"
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            f"COTAHIST_A{today.year}.TXT",
            _quote_record(
                quote_date=(today - timedelta(days=10)).strftime("%Y%m%d"),
                ticker="WEGE3",
                close_cents=4800,
            ),
        )
    stale_time = (datetime.now() - timedelta(days=2)).timestamp()
    archive_path.touch()
    os.utime(archive_path, (stale_time, stale_time))
    provider = B3CotahistMarketDataProvider(cache_directory=tmp_path)

    def fail_download(_url: str, _destination: Path) -> None:
        raise MarketDataUnavailable("download oficial falhou")

    monkeypatch.setattr(provider, "_download", fail_download)

    try:
        provider.latest_price("WEGE3")
    except MarketDataUnavailable as error:
        assert "sete dias anteriores" in str(error)
        assert "renovação do arquivo COTAHIST" in str(error)
        assert "download oficial falhou" in str(error)
    else:
        raise AssertionError("Era esperado um erro de cotação com causa do refresh")
