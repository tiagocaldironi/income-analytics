"""Official B3 COTAHIST adapter with an on-disk archive cache.

The cache stores the original ZIPs, not millions of rows in the portfolio
database.  Quotes are filtered while reading the archive and only prices that
the user actually uses are persisted by the normal portfolio workflow.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from threading import RLock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

from income_analytics.application.magic_formula_market_evidence import (
    CotahistPriceEvidence,
    MarketEvidenceStatus,
)
from income_analytics.application.market_data import MarketDataUnavailable, MarketPriceObservation


class B3CotahistMarketDataProvider:
    """Read unadjusted closing prices from B3's official COTAHIST files."""

    base_url = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist"
    current_annual_archive_max_age = timedelta(hours=12)
    current_annual_archive_retry_interval = timedelta(minutes=15)

    def __init__(
        self, *, cache_directory: Path | None = None, timeout_seconds: float = 90
    ) -> None:
        configured_directory = os.getenv("INCOME_ANALYTICS_COTAHIST_CACHE")
        self._cache_directory = cache_directory or Path(
            configured_directory or "data/cotahist"
        )
        self._timeout_seconds = timeout_seconds
        self._cache_lock = RLock()
        self._current_annual_refresh_attempted_at: datetime | None = None
        self._annual_archive_refresh_errors: dict[int, str] = {}

    def preload_last_two_years(self, *, reference_date: date | None = None) -> tuple[int, ...]:
        """Ensure current and previous annual archives are locally available."""
        reference = reference_date or date.today()
        years = (reference.year - 1, reference.year)
        with self._cache_lock:
            for year in years:
                self._ensure_annual_archive(year)
        return years

    def refresh_annual_archive(self, year: int) -> Path:
        """Replace one cached annual archive after a successful official download."""
        destination = self._annual_path(year)
        with self._cache_lock:
            self._download(self._annual_url(year), destination)
        return destination

    def refresh_daily_archive(self, *, effective_date: date | None = None) -> bool:
        """Cache the official daily file when B3 has published it."""
        requested_date = effective_date or date.today()
        destination = self._daily_path(requested_date)
        with self._cache_lock:
            try:
                self._download(self._daily_url(requested_date), destination)
            except MarketDataUnavailable:
                return False
        return True

    def latest_price(self, symbol: str) -> MarketPriceObservation:
        return self.price_on(symbol, date.today())

    def latest_prices(self, symbols: tuple[str, ...]) -> dict[str, MarketPriceObservation]:
        """Scan the cached annual archive once and return each ticker's latest close."""
        today = date.today()
        series = self.history_many(symbols, start_date=today - timedelta(days=7), end_date=today)
        latest: dict[str, MarketPriceObservation] = {}
        for symbol, observations in series.items():
            if observations:
                latest[symbol] = max(observations, key=lambda item: item.effective_date)
        return latest

    def price_on(self, symbol: str, effective_date: date) -> MarketPriceObservation:
        """Return the latest official close on or before ``effective_date``.

        A seven-day window covers weekends and short holiday sequences while
        guaranteeing that a future price is never selected.
        """
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise MarketDataUnavailable("Ticker inválido para consulta histórica B3.")
        start_date = effective_date - timedelta(days=7)
        archives = self._archives_for(start_date, effective_date)
        candidates: list[tuple[date, Decimal]] = []
        for archive in archives:
            candidates.extend(
                self._prices_in_archive(
                    archive,
                    symbol=normalized_symbol,
                    start_date=start_date,
                    end_date=effective_date,
                )
            )
        if not candidates:
            refresh_error = self._annual_archive_refresh_errors.get(effective_date.year)
            detail = (
                "Não foi encontrada cotação B3 válida nos sete dias anteriores à data escolhida."
            )
            if refresh_error:
                detail += (
                    f" A renovação do arquivo COTAHIST {effective_date.year} também falhou: "
                    f"{refresh_error}"
                )
            raise MarketDataUnavailable(
                detail
            )
        observed_date, close = max(candidates, key=lambda item: item[0])
        return MarketPriceObservation(
            symbol=normalized_symbol,
            price=close,
            currency_code="BRL",
            effective_date=observed_date,
            source="b3_cotahist",
        )

    def price_evidence_on(
        self, symbol: str, requested_reference_date: date
    ) -> CotahistPriceEvidence:
        """Return the official close and deterministic location in COTAHIST.

        Unlike :meth:`price_on`, this method keeps the archive member and line
        number so an audit can retrieve the exact source record.
        """
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise MarketDataUnavailable("Ticker inválido para consulta histórica B3.")
        start_date = requested_reference_date - timedelta(days=7)
        candidates: list[tuple[date, Decimal, Path, str, int]] = []
        for archive in self._archives_for(start_date, requested_reference_date):
            candidates.extend(
                self._price_evidence_in_archive(
                    archive,
                    symbol=normalized_symbol,
                    start_date=start_date,
                    end_date=requested_reference_date,
                )
            )
        if not candidates:
            raise MarketDataUnavailable(
                "Não foi encontrada cotação B3 válida nos sete dias anteriores à data escolhida."
            )
        observed_date, close, archive, member, line_number = max(
            candidates, key=lambda item: item[0]
        )
        return CotahistPriceEvidence(
            ticker=normalized_symbol,
            requested_reference_date=requested_reference_date,
            effective_date=observed_date,
            price=close,
            currency="BRL",
            source="B3_COTAHIST",
            source_file=archive.name,
            record_reference=(
                f"{archive.name}|{member}|line={line_number}|date={observed_date:%Y%m%d}"
                f"|ticker={normalized_symbol}|close={close}"
            ),
            status=MarketEvidenceStatus.VALID,
        )

    def history(
        self, symbol: str, *, start_date: date, end_date: date
    ) -> tuple[MarketPriceObservation, ...]:
        """Return the persisted-source daily close series for one B3 ticker."""
        series = self.history_many(
            (symbol,), start_date=start_date, end_date=end_date
        ).get(symbol.strip().upper(), ())
        if not series:
            raise MarketDataUnavailable("Não foi encontrada série histórica B3 para este ativo.")
        return series

    def history_many(
        self, symbols: tuple[str, ...] | list[str] | set[str], *,
        start_date: date, end_date: date,
    ) -> dict[str, tuple[MarketPriceObservation, ...]]:
        """Read several tickers by scanning each cached archive only once."""
        if end_date < start_date:
            raise MarketDataUnavailable("Período histórico inválido.")
        normalized = {symbol.strip().upper() for symbol in symbols if symbol.strip()}
        if not normalized:
            return {}
        by_symbol: dict[str, dict[date, Decimal]] = {symbol: {} for symbol in normalized}
        for archive in self._archives_for(start_date, end_date):
            self._prices_for_symbols_in_archive(
                archive, symbols=normalized, start_date=start_date, end_date=end_date,
                result=by_symbol,
            )
        return {
            symbol: tuple(
                MarketPriceObservation(
                    symbol=symbol, price=close, currency_code="BRL",
                    effective_date=quote_date, source="b3_cotahist",
                )
                for quote_date, close in sorted(prices.items())
            )
            for symbol, prices in by_symbol.items() if prices
        }

    def _prices_for_symbols_in_archive(
        self, archive_path: Path, *, symbols: set[str], start_date: date,
        end_date: date, result: dict[str, dict[date, Decimal]],
    ) -> None:
        try:
            with ZipFile(archive_path) as archive:
                text_entry = next(
                    (name for name in archive.namelist() if name.upper().endswith(".TXT")), None
                )
                if text_entry is None:
                    raise BadZipFile("Arquivo COTAHIST sem TXT.")
                with archive.open(text_entry) as records:
                    for raw_record in records:
                        if raw_record[:2] != b"01":
                            continue
                        symbol = raw_record[12:24].decode("latin-1").strip()
                        if symbol not in symbols:
                            continue
                        raw_date = raw_record[2:10].decode("ascii")
                        quote_date = date(
                            int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8])
                        )
                        if not start_date <= quote_date <= end_date:
                            continue
                        close = Decimal(raw_record[108:121].decode("ascii")) / Decimal("100")
                        if close > 0:
                            result[symbol][quote_date] = close
        except (BadZipFile, OSError, UnicodeDecodeError, ValueError) as error:
            raise MarketDataUnavailable(
                "Não foi possível processar o arquivo histórico da B3."
            ) from error

    def _archives_for(self, start_date: date, end_date: date) -> tuple[Path, ...]:
        archives: list[Path] = []
        for path in (self._daily_path(end_date),):
            if path.exists():
                archives.append(path)
        for year in range(start_date.year, end_date.year + 1):
            archives.append(self._ensure_annual_archive(year))
        return tuple(archives)

    def _ensure_annual_archive(self, year: int) -> Path:
        with self._cache_lock:
            destination = self._annual_path(year)
            if destination.exists() and destination.stat().st_size > 0:
                is_current_year = year == date.today().year
                now = datetime.now()
                age = now.timestamp() - destination.stat().st_mtime
                last_attempt = self._current_annual_refresh_attempted_at
                retry_due = (
                    last_attempt is None
                    or now - last_attempt >= self.current_annual_archive_retry_interval
                )
                if (
                    is_current_year
                    and age > self.current_annual_archive_max_age.total_seconds()
                    and retry_due
                ):
                    # B3 updates the current year's annual archive as sessions close.
                    # Reusing an old but valid ZIP forever made COTAHIST appear empty
                    # for recent dates after the cached file stopped receiving updates.
                    # _download writes atomically; on failure keep the previous cache.
                    self._current_annual_refresh_attempted_at = now
                    try:
                        self._download(self._annual_url(year), destination)
                    except MarketDataUnavailable as error:
                        cause = error.__cause__
                        self._annual_archive_refresh_errors[year] = (
                            f"{type(cause).__name__}: {cause}"
                            if cause
                            else str(error)
                        )
                    else:
                        self._current_annual_refresh_attempted_at = None
                        self._annual_archive_refresh_errors.pop(year, None)
                return destination
            self._download(self._annual_url(year), destination)
            return destination

    def _download(self, url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(f"{destination.suffix}.part")
        try:
            request = Request(url, headers={"User-Agent": "IncomeAnalytics/1.0"})
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = response.read()
            with ZipFile(BytesIO(payload)) as archive:
                if not archive.namelist():
                    raise BadZipFile("Arquivo COTAHIST sem conteúdo.")
            temporary.write_bytes(payload)
            temporary.replace(destination)
        except (HTTPError, URLError, OSError, BadZipFile, ValueError) as error:
            if temporary.exists():
                temporary.unlink()
            raise MarketDataUnavailable("Arquivo histórico oficial da B3 indisponível.") from error

    def _prices_in_archive(
        self, archive_path: Path, *, symbol: str, start_date: date, end_date: date
    ) -> list[tuple[date, Decimal]]:
        prices: list[tuple[date, Decimal]] = []
        try:
            with ZipFile(archive_path) as archive:
                text_entry = next(
                    (name for name in archive.namelist() if name.upper().endswith(".TXT")), None
                )
                if text_entry is None:
                    raise BadZipFile("Arquivo COTAHIST sem TXT.")
                with archive.open(text_entry) as records:
                    for raw_record in records:
                        if raw_record[:2] != b"01":
                            continue
                        if raw_record[12:24].decode("latin-1").strip() != symbol:
                            continue
                        raw_date = raw_record[2:10].decode("ascii")
                        quote_date = date(
                            int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8])
                        )
                        if not start_date <= quote_date <= end_date:
                            continue
                        close = Decimal(raw_record[108:121].decode("ascii")) / Decimal("100")
                        if close > 0:
                            prices.append((quote_date, close))
        except (BadZipFile, OSError, UnicodeDecodeError, ValueError) as error:
            raise MarketDataUnavailable(
                "Não foi possível processar o arquivo histórico da B3."
            ) from error
        return prices

    def _price_evidence_in_archive(
        self, archive_path: Path, *, symbol: str, start_date: date, end_date: date
    ) -> list[tuple[date, Decimal, Path, str, int]]:
        prices: list[tuple[date, Decimal, Path, str, int]] = []
        try:
            with ZipFile(archive_path) as archive:
                text_entry = next(
                    (name for name in archive.namelist() if name.upper().endswith(".TXT")), None
                )
                if text_entry is None:
                    raise BadZipFile("Arquivo COTAHIST sem TXT.")
                with archive.open(text_entry) as records:
                    for line_number, raw_record in enumerate(records, start=1):
                        if raw_record[:2] != b"01":
                            continue
                        if raw_record[12:24].decode("latin-1").strip() != symbol:
                            continue
                        raw_date = raw_record[2:10].decode("ascii")
                        quote_date = date(
                            int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8])
                        )
                        if not start_date <= quote_date <= end_date:
                            continue
                        close = Decimal(raw_record[108:121].decode("ascii")) / Decimal("100")
                        if close > 0:
                            prices.append(
                                (quote_date, close, archive_path, text_entry, line_number)
                            )
        except (BadZipFile, OSError, UnicodeDecodeError, ValueError) as error:
            raise MarketDataUnavailable(
                "Não foi possível processar o arquivo histórico da B3."
            ) from error
        return prices

    def _annual_path(self, year: int) -> Path:
        return self._cache_directory / f"COTAHIST_A{year}.ZIP"

    def _daily_path(self, effective_date: date) -> Path:
        return self._cache_directory / f"COTAHIST_D{effective_date:%d%m%Y}.ZIP"

    def _annual_url(self, year: int) -> str:
        return f"{self.base_url}/COTAHIST_A{year}.ZIP"

    def _daily_url(self, effective_date: date) -> str:
        return f"{self.base_url}/COTAHIST_D{effective_date:%d%m%Y}.ZIP"
