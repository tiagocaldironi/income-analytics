"""Reusable, lossless parsers for B3 negotiation and movement workbooks.

The parsers deliberately do *not* decide an asset class or apply operations.
That belongs to the import service, after it has resolved the asset against the
registry.  Keeping this boundary small makes a B3 preview auditable: every
non-empty source row is returned with an explicit status.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from io import BytesIO
from typing import Final
from zipfile import BadZipFile, ZipFile

from income_analytics.infrastructure.irpf_xlsx_import import (
    _column_for,
    _normalized,
    _shared_strings,
    _sheet_path,
    _worksheet_rows,
)


class B3RowStatus(StrEnum):
    NEW = "NEW"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID = "INVALID"


class B3LayoutError(ValueError):
    """A B3 workbook whose required named columns are not present."""

    code: Final[str] = "INVALID_B3_LAYOUT"


@dataclass(frozen=True, slots=True)
class B3ParsedRow:
    report_type: str
    source_row: int
    status: B3RowStatus
    source_symbol: str | None = None
    normalized_symbol: str | None = None
    event_date: date | None = None
    event_type: str | None = None
    income_type: str | None = None
    institution: str | None = None
    market: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    total_value: Decimal | None = None
    gross_amount: Decimal | None = None
    withheld_tax: Decimal | None = None
    detail: str | None = None
    original_movement: str | None = None
    direction: str | None = None
    source_date_type: str | None = None
    quantity_status: str | None = None
    financial_status: str | None = None


_NEGOTIATION_COLUMNS: Final[dict[str, tuple[str, ...]]] = {
    "date": ("DATADONEGOCIO",),
    "movement": ("TIPODEMOVIMENTACAO",),
    "market": ("MERCADO",),
    "institution": ("INSTITUICAO",),
    "symbol": ("CODIGODENEGOCIACAO",),
    "quantity": ("QUANTIDADE",),
    "unit_price": ("PRECO",),
    "total_value": ("VALOR",),
}
_MOVEMENT_COLUMNS: Final[dict[str, tuple[str, ...]]] = {
    "date": ("DATA",),
    "movement": ("MOVIMENTACAO",),
    "product": ("PRODUTO",),
    "institution": ("INSTITUICAO",),
    "quantity": ("QUANTIDADE",),
    "unit_price": ("PRECOUNITARIO",),
    "total_value": ("VALORDAOPERACAO", "VALOR"),
}


def _columns(header: dict[int, str], required: dict[str, tuple[str, ...]]) -> dict[str, int]:
    resolved: dict[str, int] = {}
    for field, names in required.items():
        column = _column_for(header, lambda value: value in names)
        if column is None:
            raise B3LayoutError(f"{B3LayoutError.code}: coluna obrigatória ausente ({field}).")
        resolved[field] = column
    return resolved


def _load_rows(workbook: bytes, *sheet_names: str) -> list[dict[int, str]]:
    try:
        with ZipFile(BytesIO(workbook)) as archive:
            for sheet_name in sheet_names:
                try:
                    return _worksheet_rows(
                        archive.read(_sheet_path(archive, sheet_name)), _shared_strings(archive)
                    )
                except KeyError:
                    continue
            raise KeyError(sheet_names[0])
    except (BadZipFile, KeyError, ValueError) as error:
        raise B3LayoutError(
            f"{B3LayoutError.code}: arquivo inválido ou sem aba {sheet_name}."
        ) from error


def _cell(row: dict[int, str], column: int) -> str:
    return row.get(column, "").strip()


def _decimal(value: str) -> Decimal | None:
    text = value.replace("R$", "").replace("\u00a0", "").strip()
    if not text or text == "-":
        return None
    # B3 exports commonly use dot decimal separators.  Accept Brazilian
    # formatting too, while never routing through float.
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _date(value: str) -> date | None:
    for pattern in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    return None


def _product_symbol(value: str) -> str | None:
    symbol = value.split(" - ", 1)[0].strip().upper()
    return symbol or None


class B3NegotiationReportParser:
    report_type: Final[str] = "NEGOTIATION"

    def parse(self, workbook: bytes) -> tuple[B3ParsedRow, ...]:
        rows = _load_rows(workbook, "Negociação", "Negociações")
        if not rows:
            raise B3LayoutError(f"{B3LayoutError.code}: planilha sem cabeçalho.")
        columns = _columns(rows[0], _NEGOTIATION_COLUMNS)
        parsed: list[B3ParsedRow] = []
        for source_row, row in enumerate(rows[1:], start=2):
            if not any(value.strip() for value in row.values()):
                continue
            source_symbol = _cell(row, columns["symbol"]).upper() or None
            market = _cell(row, columns["market"]) or None
            normalized_symbol = source_symbol
            is_fractional = _normalized(market or "") == "MERCADOFRACIONARIO"
            if source_symbol and is_fractional and source_symbol.endswith("F"):
                normalized_symbol = source_symbol[:-1]
            movement = _normalized(_cell(row, columns["movement"]))
            event_type = {"COMPRA": "BUY", "VENDA": "SELL"}.get(movement)
            event_date = _date(_cell(row, columns["date"]))
            quantity = _decimal(_cell(row, columns["quantity"]))
            unit_price = _decimal(_cell(row, columns["unit_price"]))
            total_value = _decimal(_cell(row, columns["total_value"]))
            status, detail = B3RowStatus.NEW, None
            if event_type is None:
                status, detail = B3RowStatus.UNSUPPORTED, "Tipo de negociação não suportado."
            elif not source_symbol or event_date is None or quantity is None or unit_price is None:
                status, detail = B3RowStatus.INVALID, "Campos obrigatórios inválidos na negociação."
            elif quantity <= 0 or unit_price <= 0:
                status, detail = B3RowStatus.INVALID, "Quantidade e preço devem ser positivos."
            parsed.append(
                B3ParsedRow(
                    report_type=self.report_type,
                    source_row=source_row,
                    status=status,
                    source_symbol=source_symbol,
                    normalized_symbol=normalized_symbol,
                    event_date=event_date,
                    event_type=event_type,
                    institution=_cell(row, columns["institution"]) or None,
                    market=market,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_value=total_value,
                    detail=detail,
                )
            )
        return tuple(parsed)


class B3MovementReportParser:
    report_type: Final[str] = "MOVEMENT"

    def parse(self, workbook: bytes) -> tuple[B3ParsedRow, ...]:
        rows = _load_rows(workbook, "Movimentação", "Movimentações")
        if not rows:
            raise B3LayoutError(f"{B3LayoutError.code}: planilha sem cabeçalho.")
        columns = _columns(rows[0], _MOVEMENT_COLUMNS)
        direction_column = _column_for(rows[0], lambda value: value == "ENTRADASAIDA")
        parsed: list[B3ParsedRow] = []
        for source_row, row in enumerate(rows[1:], start=2):
            if not any(value.strip() for value in row.values()):
                continue
            original_movement = _cell(row, columns["movement"]) or None
            movement = _normalized(original_movement or "")
            direction = (
                _normalized(_cell(row, direction_column)) if direction_column is not None else ""
            )
            income_type = {
                "DIVIDENDO": "DIVIDEND",
                "JUROSSOBRECAPITALPROPRIO": "JCP",
                "RENDIMENTO": "INCOME",
            }.get(movement)
            # Compra/Venda state the economic side explicitly.  Settlement
            # transfers are handled below by their own exact movement type.
            event_type = {"COMPRA": "BUY", "VENDA": "SELL"}.get(movement)
            source_symbol = _product_symbol(_cell(row, columns["product"]))
            event_date = _date(_cell(row, columns["date"]))
            quantity = _decimal(_cell(row, columns["quantity"]))
            unit_price = _decimal(_cell(row, columns["unit_price"]))
            total_value = _decimal(_cell(row, columns["total_value"]))
            status, detail = B3RowStatus.NEW, None
            gross_amount = withheld_tax = None
            if movement == "TRANSFERENCIALIQUIDACAO":
                event_type = {"CREDITO": "BUY", "DEBITO": "SELL"}.get(direction)
                if not source_symbol or event_date is None or quantity is None or quantity <= 0:
                    status, detail = (
                        B3RowStatus.INVALID,
                        "Quantidade ou identificação inválida na liquidação.",
                    )
                elif event_type is None:
                    status, detail = B3RowStatus.REVIEW_REQUIRED, "DIRECAO_LIQUIDACAO_DESCONHECIDA"
            elif event_type is not None:
                if (
                    not source_symbol
                    or event_date is None
                    or quantity is None
                    or unit_price is None
                    or total_value is None
                    or quantity <= 0
                    or unit_price <= 0
                    or total_value <= 0
                ):
                    status, detail = (
                        B3RowStatus.INVALID,
                        "Campos obrigatórios inválidos na operação.",
                    )
            elif income_type is None:
                status, detail = (
                    (B3RowStatus.UNSUPPORTED, "CUSTODY_TRANSFER")
                    if movement == "TRANSFERENCIA"
                    else (B3RowStatus.UNSUPPORTED, "STOCK_LOAN")
                    if movement == "EMPRESTIMO"
                    else (B3RowStatus.REVIEW_REQUIRED, "RECONCILIATION_REFERENCE")
                    if movement == "ATUALIZACAO"
                    else (B3RowStatus.UNSUPPORTED, "Tipo de movimentação não suportado.")
                )
            elif not source_symbol or event_date is None or total_value is None:
                status, detail = B3RowStatus.INVALID, "Campos obrigatórios inválidos no provento."
            elif income_type == "JCP":
                if quantity is None or unit_price is None:
                    status, detail = B3RowStatus.REVIEW_REQUIRED, "JCP sem base bruta verificável."
                else:
                    gross_amount = quantity * unit_price
                    if gross_amount < total_value:
                        status, detail = (
                            B3RowStatus.REVIEW_REQUIRED,
                            "JCP líquido maior que o bruto informado.",
                        )
                    else:
                        withheld_tax = gross_amount - total_value
            parsed.append(
                B3ParsedRow(
                    report_type=self.report_type,
                    source_row=source_row,
                    status=status,
                    source_symbol=source_symbol,
                    normalized_symbol=source_symbol,
                    event_date=event_date,
                    event_type=event_type,
                    income_type=income_type,
                    institution=_cell(row, columns["institution"]) or None,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_value=total_value,
                    gross_amount=gross_amount,
                    withheld_tax=withheld_tax,
                    detail=detail,
                    original_movement=original_movement,
                    direction=direction or None,
                    source_date_type="SETTLEMENT_DATE"
                    if movement == "TRANSFERENCIALIQUIDACAO"
                    else None,
                    quantity_status=("COMPLETE" if movement == "TRANSFERENCIALIQUIDACAO" else None),
                    financial_status=(
                        "DATA_GAP"
                        if movement == "TRANSFERENCIALIQUIDACAO"
                        and (unit_price is None or total_value is None)
                        else "COMPLETE"
                        if movement == "TRANSFERENCIALIQUIDACAO"
                        else None
                    ),
                )
            )
        return tuple(parsed)
