"""Read Brazilian stock trades from the B3 negotiation spreadsheet."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from zipfile import BadZipFile, ZipFile

from income_analytics.infrastructure.irpf_xlsx_import import (
    _column_for,
    _normalized,
    _sheet_path,
    _shared_strings,
    _worksheet_rows,
)

_STOCK = re.compile(r"^[A-Z]{4}[3-8]F?$")


@dataclass(frozen=True, slots=True)
class B3BrazilianStockTrade:
    ticker: str
    event_type: str
    quantity: Decimal
    unit_price: Decimal
    effective_date: datetime


def parse_b3_brazilian_stock_trades(workbook: bytes) -> tuple[B3BrazilianStockTrade, ...]:
    try:
        with ZipFile(BytesIO(workbook)) as archive:
            rows = _worksheet_rows(
                archive.read(_sheet_path(archive, "Negociação")), _shared_strings(archive)
            )
    except (BadZipFile, KeyError, ValueError) as error:
        raise ValueError("Arquivo B3 inválido ou sem a aba Negociação.") from error
    header = rows[0]
    date_column = _column_for(header, lambda value: value == "DATADONEGOCIO")
    movement_column = _column_for(header, lambda value: value == "TIPODEMOVIMENTACAO")
    ticker_column = _column_for(header, lambda value: value == "CODIGODENEGOCIACAO")
    quantity_column = _column_for(header, lambda value: value == "QUANTIDADE")
    price_column = _column_for(header, lambda value: value == "PRECO")
    if None in {date_column, movement_column, ticker_column, quantity_column, price_column}:
        raise ValueError("A planilha B3 não contém as colunas de negociação esperadas.")
    trades = []
    for row in rows[1:]:
        raw_ticker = row.get(ticker_column, "").strip().upper()
        if not _STOCK.fullmatch(raw_ticker):
            continue
        movement = _normalized(row.get(movement_column, ""))
        if movement not in {"COMPRA", "VENDA"}:
            continue
        try:
            quantity = Decimal(row.get(quantity_column, ""))
            price = Decimal(row.get(price_column, ""))
            effective_date = datetime.strptime(row.get(date_column, ""), "%d/%m/%Y")
        except (InvalidOperation, ValueError):
            continue
        if quantity > 0 and price > 0:
            trades.append(B3BrazilianStockTrade(
                ticker=raw_ticker.removesuffix("F"), event_type="BUY" if movement == "COMPRA" else "SELL",
                quantity=quantity, unit_price=price, effective_date=effective_date,
            ))
    if not trades:
        raise ValueError("Não encontrei negociações de ações brasileiras na planilha B3.")
    return tuple(trades)
