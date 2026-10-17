"""Official B3 historical index observations for IBOV and IFIX."""

from __future__ import annotations

import re
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from income_analytics.application.benchmark_data import (
    BenchmarkDataUnavailable,
    BenchmarkObservation,
)

_MONTHS = {
    "JAN": 1,
    "FEV": 2,
    "MAR": 3,
    "ABR": 4,
    "MAI": 5,
    "JUN": 6,
    "JUL": 7,
    "AGO": 8,
    "SET": 9,
    "OUT": 10,
    "NOV": 11,
    "DEZ": 12,
}
_PAGE_CODES = {"IBOV": "IBOVESPA", "IFIX": "IFIX"}


class _IndexTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self.heading_parts: list[str] = []
        self._in_heading = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
        elif tag in {"h1", "h2", "h3", "h4"}:
            self._in_heading = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None
        elif tag in {"h1", "h2", "h3", "h4"}:
            self._in_heading = False

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)
        if self._in_heading:
            self.heading_parts.append(data)


def _number(value: str) -> Decimal | None:
    normalized = value.replace(".", "").replace(",", ".").strip()
    if not normalized:
        return None
    try:
        amount = Decimal(normalized)
    except InvalidOperation:
        return None
    return amount if amount.is_finite() and amount > 0 else None


def parse_b3_index_table(
    html: str, *, benchmark: str, year: int, start_date: date, end_date: date
) -> tuple[BenchmarkObservation, ...]:
    """Parse the official B3 daily-evolution table without filling absent days."""
    parser = _IndexTableParser()
    parser.feed(html)
    headings = " ".join(parser.heading_parts)
    heading_code = _PAGE_CODES.get(benchmark.upper(), benchmark)
    if not re.search(rf"\b{re.escape(heading_code)}\b.*\b{year}\b", headings, re.IGNORECASE):
        raise BenchmarkDataUnavailable("A B3 retornou uma tabela sem o ano solicitado.")
    month_columns: list[tuple[int, int]] = []
    for row in parser.rows:
        if row and row[0].strip().casefold() == "dia":
            month_columns = [
                (index, _MONTHS[value.strip().upper()[:3]])
                for index, value in enumerate(row[1:], start=1)
                if value.strip().upper()[:3] in _MONTHS
            ]
            break
    if not month_columns:
        raise BenchmarkDataUnavailable("A tabela de evolução diária da B3 mudou de formato.")

    observations: dict[date, BenchmarkObservation] = {}
    for row in parser.rows:
        if not row or not row[0].strip().isdigit():
            continue
        day = int(row[0].strip())
        for column, month in month_columns:
            if column >= len(row):
                continue
            value = _number(row[column])
            if value is None:
                continue
            try:
                observed = date(year, month, day)
            except ValueError:
                continue
            if start_date <= observed <= end_date:
                observations[observed] = BenchmarkObservation(
                    benchmark=benchmark,
                    effective_date=observed,
                    value=value,
                    nature="INDEX_LEVEL",
                    source="b3",
                )
    return tuple(observations[key] for key in sorted(observations))


class B3BenchmarkDataProvider:
    """Fetch benchmark index history from B3's public daily-evolution tables."""

    _base_url = "https://sistemaswebb3-listados.b3.com.br/indexStatisticsPage/daily-evolution"

    def __init__(self, *, timeout_seconds: float = 15) -> None:
        self._timeout_seconds = timeout_seconds

    def observations(
        self, benchmark: str, *, start_date: date, end_date: date
    ) -> tuple[BenchmarkObservation, ...]:
        name = benchmark.upper()
        page_code = _PAGE_CODES.get(name)
        if page_code is None:
            raise BenchmarkDataUnavailable(f"Índice B3 não suportado: {name}.")
        if end_date < start_date:
            raise ValueError("A data final deve ser posterior à data inicial.")

        observations: dict[date, BenchmarkObservation] = {}
        for year in range(start_date.year, end_date.year + 1):
            for semester in (1, 2):
                semester_start = date(year, 1 if semester == 1 else 7, 1)
                last_month = 6 if semester == 1 else 12
                semester_end = date(year, last_month, monthrange(year, last_month)[1])
                if semester_end < start_date or semester_start > end_date:
                    continue
                params = urlencode({"language": "pt-br", "year": year, "semester": semester})
                url = f"{self._base_url}/{page_code}?{params}"
                request = Request(url, headers={"User-Agent": "IncomeAnalytics/1.0"})
                try:
                    with urlopen(request, timeout=self._timeout_seconds) as response:
                        html = response.read().decode("utf-8")
                    parsed = parse_b3_index_table(
                        html,
                        benchmark=name,
                        year=year,
                        start_date=max(start_date, semester_start),
                        end_date=min(end_date, semester_end),
                    )
                except (OSError, URLError, UnicodeDecodeError) as error:
                    raise BenchmarkDataUnavailable(
                        f"Não foi possível consultar o histórico {name} na B3."
                    ) from error
                observations.update((item.effective_date, item) for item in parsed)
        if not observations:
            raise BenchmarkDataUnavailable(f"A B3 não retornou observações de {name} no período.")
        return tuple(observations[key] for key in sorted(observations))
