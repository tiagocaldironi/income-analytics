"""Read the Brazilian-stock position block from an Investidor10 IRPF workbook."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import PurePosixPath
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_TICKER = re.compile(r"^[A-Z]{4}\d{1,2}$")


@dataclass(frozen=True, slots=True)
class IrpfBrazilianStockPosition:
    ticker: str
    name: str
    quantity: Decimal
    total_cost: Decimal

    @property
    def unit_price(self) -> Decimal:
        return self.total_cost / self.quantity


def parse_irpf_brazilian_stocks(workbook: bytes) -> tuple[IrpfBrazilianStockPosition, ...]:
    """Parse only ``Bens e Direitos / Ações`` from a generated IRPF workbook."""
    try:
        with ZipFile(BytesIO(workbook)) as archive:
            shared = _shared_strings(archive)
            sheet_path = _sheet_path(archive, "Bens e Direitos")
            rows = _worksheet_rows(archive.read(sheet_path), shared)
    except (BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise ValueError("Arquivo IRPF inválido ou sem a aba Bens e Direitos.") from error

    header_index = next(
        (
            index
            for index, row in enumerate(rows)
            if "CODIGO" in {_normalized(value) for value in row.values()}
            and any(_normalized(value).startswith("QDE") for value in row.values())
            and any(_normalized(value).startswith("CNPJ") for value in row.values())
        ),
        None,
    )
    if header_index is None:
        raise ValueError("Não encontrei a tabela de ações brasileiras em Bens e Direitos.")

    header = rows[header_index]
    code_column = _column_for(header, lambda value: value == "CODIGO")
    quantity_column = _column_for(header, lambda value: value.startswith("QDE"))
    final_value_column = _column_for(header, lambda value: value.startswith("SITUACAOEM31122025"))
    if code_column is None or quantity_column is None or final_value_column is None:
        raise ValueError("A tabela de ações brasileiras não contém quantidade e posição final.")

    positions: list[IrpfBrazilianStockPosition] = []
    for row in rows[header_index + 1 :]:
        if not any(row.values()):
            break
        ticker = row.get(code_column, "").strip().upper()
        if not _TICKER.fullmatch(ticker):
            continue
        quantity = _decimal(row.get(quantity_column, ""))
        total_cost = _brl_decimal(row.get(final_value_column, ""))
        if quantity is None or total_cost is None or quantity <= 0 or total_cost <= 0:
            continue
        name = row.get(0, ticker).strip() or ticker
        positions.append(IrpfBrazilianStockPosition(ticker, name, quantity, total_cost))
    if not positions:
        raise ValueError("Não encontrei posições válidas de ações brasileiras para importar.")
    return tuple(positions)


def _sheet_path(archive: ZipFile, name: str) -> str:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        relationship.attrib["Id"]: relationship.attrib["Target"] for relationship in relationships
    }
    for sheet in workbook.findall("main:sheets/main:sheet", _NS):
        if sheet.attrib.get("name") != name:
            continue
        target = targets[sheet.attrib[f"{{{_REL_NS}}}id"]]
        return str(PurePosixPath("xl") / target)
    raise KeyError(name)


def _shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(item.itertext()) for item in root.findall("main:si", _NS)]


def _worksheet_rows(xml: bytes, shared: list[str]) -> list[dict[int, str]]:
    root = ElementTree.fromstring(xml)
    rows: list[dict[int, str]] = []
    for row in root.findall("main:sheetData/main:row", _NS):
        values: dict[int, str] = {}
        for cell in row.findall("main:c", _NS):
            column = _column_index(cell.attrib["r"])
            value = cell.findtext("main:v", default="", namespaces=_NS)
            if cell.attrib.get("t") == "s" and value:
                value = shared[int(value)]
            elif cell.attrib.get("t") == "inlineStr":
                value = "".join(cell.itertext())
            values[column] = value.strip()
        rows.append(values)
    return rows


def _column_index(reference: str) -> int:
    letters = "".join(character for character in reference if character.isalpha())
    result = 0
    for letter in letters:
        result = result * 26 + ord(letter.upper()) - ord("A") + 1
    return result - 1


def _column_for(header: dict[int, str], predicate: Callable[[str], bool]) -> int | None:
    return next((column for column, value in header.items() if predicate(_normalized(value))), None)


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.upper())
    return "".join(
        character
        for character in decomposed
        if character.isalnum() and not unicodedata.combining(character)
    )


def _decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


def _brl_decimal(value: str) -> Decimal | None:
    cleaned = value.replace("R$", "").replace("\u00a0", "").strip()
    if cleaned in {"", "-"}:
        return None
    return _decimal(cleaned)
