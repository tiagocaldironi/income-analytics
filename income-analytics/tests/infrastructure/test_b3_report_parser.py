from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from income_analytics.infrastructure.b3_report_parser import (
    B3LayoutError,
    B3MovementReportParser,
    B3NegotiationReportParser,
    B3RowStatus,
)


def _workbook(sheet: str, header: list[str], rows: list[list[str]]) -> bytes:
    """Small XLSX fixture with inline strings, avoiding a test-only dependency."""

    def cells(values: list[str], row_number: int) -> str:
        return "".join(
            f'<c r="{chr(65 + index)}{row_number}" t="inlineStr"><is><t>{value}</t></is></c>'
            for index, value in enumerate(values)
        )

    worksheet = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        f'<row r="1">{cells(header, 1)}</row>'
        + "".join(f'<row r="{i}">{cells(row, i)}</row>' for i, row in enumerate(rows, 2))
        + "</sheetData></worksheet>"
    )
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "xl/workbook.xml",
            f'''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>
            <sheet name="{sheet}" sheetId="1" r:id="rId1"/></sheets></workbook>''',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/>'
            "</Relationships>",
        )
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return output.getvalue()


def test_negotiation_uses_named_columns_and_only_normalizes_fractional_market() -> None:
    header = [
        "Preço",
        "Mercado",
        "Código de Negociação",
        "Quantidade",
        "Data do Negócio",
        "Instituição",
        "Tipo de Movimentação",
        "Valor",
    ]
    workbook = _workbook(
        "Negociação",
        header,
        [
            [
                "10.50",
                "Mercado Fracionário",
                "BBSE3F",
                "3",
                "03/09/2026",
                "Corretora",
                "Compra",
                "31.50",
            ],
            ["10", "Mercado à Vista", "TESTF", "1", "04/09/2026", "Corretora", "Venda", "10"],
        ],
    )
    first, second = B3NegotiationReportParser().parse(workbook)
    assert first.status is B3RowStatus.NEW
    assert first.source_symbol == "BBSE3F"
    assert first.normalized_symbol == "BBSE3"
    assert first.quantity == Decimal("3")
    assert first.unit_price == Decimal("10.50")
    assert first.institution == "Corretora"
    assert second.normalized_symbol == "TESTF"


def test_missing_required_column_is_invalid_b3_layout() -> None:
    workbook = _workbook("Negociação", ["Data do Negócio"], [["03/09/2026"]])
    with pytest.raises(B3LayoutError, match="INVALID_B3_LAYOUT"):
        B3NegotiationReportParser().parse(workbook)


def test_movement_jcp_uses_decimal_and_preserves_institution() -> None:
    header = [
        "Valor da Operação",
        "Produto",
        "Movimentação",
        "Quantidade",
        "Data",
        "Preço unitário",
        "Instituição",
    ]
    workbook = _workbook(
        "Movimentação",
        header,
        [
            [
                "30.24",
                "ITSA4 - ITAUSA",
                "Juros Sobre Capital Próprio",
                "316",
                "28/08/2026",
                "0.116",
                "NU",
            ]
        ],
    )
    row = B3MovementReportParser().parse(workbook)[0]
    assert row.status is B3RowStatus.NEW
    assert row.income_type == "JCP"
    assert row.gross_amount == Decimal("36.656")
    assert row.withheld_tax == Decimal("6.416")
    assert row.total_value == Decimal("30.24")
    assert row.institution == "NU"


def test_movement_jcp_without_gross_evidence_requires_review() -> None:
    header = [
        "Data",
        "Movimentação",
        "Produto",
        "Instituição",
        "Quantidade",
        "Preço unitário",
        "Valor da Operação",
    ]
    workbook = _workbook(
        "Movimentação",
        header,
        [
            [
                "01/01/2026",
                "Juros Sobre Capital Próprio",
                "ABCD3 - Teste",
                "NU",
                "-",
                "-",
                "10",
            ]
        ],
    )
    row = B3MovementReportParser().parse(workbook)[0]
    assert row.status is B3RowStatus.REVIEW_REQUIRED
    assert row.gross_amount is None


def test_rendimento_is_generic_income_not_fii_income() -> None:
    header = [
        "Data",
        "Movimentação",
        "Produto",
        "Instituição",
        "Quantidade",
        "Preço unitário",
        "Valor da Operação",
    ]
    workbook = _workbook(
        "Movimentação",
        header,
        [
            [
                "01/01/2026",
                "Rendimento",
                "IVVB11 - ETF",
                "NU",
                "1",
                "1",
                "1",
            ]
        ],
    )
    row = B3MovementReportParser().parse(workbook)[0]
    assert row.status is B3RowStatus.NEW
    assert row.income_type == "INCOME"


def test_settlement_is_an_economic_trade_and_preserves_financial_gaps() -> None:
    header = [
        "Entrada/Saída",
        "Data",
        "Movimentação",
        "Produto",
        "Instituição",
        "Quantidade",
        "Preço unitário",
        "Valor da Operação",
    ]
    buy, sell, incomplete = B3MovementReportParser().parse(
        _workbook(
            "Movimentações",
            header,
            [
                [
                    "Crédito",
                    "01/01/2026",
                    "Transferência - Liquidação",
                    "ITSA4 - Itaú",
                    "XP",
                    "2",
                    "10",
                    "20",
                ],
                [
                    "Débito",
                    "02/01/2026",
                    "Transferência - Liquidação",
                    "ITSA4 - Itaú",
                    "XP",
                    "2",
                    "10",
                    "20",
                ],
                [
                    "Débito",
                    "03/01/2026",
                    "Transferência - Liquidação",
                    "ITSA4 - Itaú",
                    "XP",
                    "2",
                    "-",
                    "-",
                ],
            ],
        )
    )
    assert (buy.status, buy.event_type, buy.source_date_type) == (
        B3RowStatus.NEW,
        "BUY",
        "SETTLEMENT_DATE",
    )
    assert (sell.status, sell.event_type) == (B3RowStatus.NEW, "SELL")
    assert incomplete.status is B3RowStatus.NEW
    assert incomplete.event_type == "SELL"
    assert incomplete.quantity == Decimal("2")
    assert incomplete.unit_price is None
    assert incomplete.total_value is None
    assert incomplete.quantity_status == "COMPLETE"
    assert incomplete.financial_status == "DATA_GAP"


def test_explicit_purchase_and_sale_in_movement_are_economic_trades() -> None:
    header = [
        "Entrada/Saída",
        "Data",
        "Movimentação",
        "Produto",
        "Instituição",
        "Quantidade",
        "Preço unitário",
        "Valor",
    ]
    purchase, sale = B3MovementReportParser().parse(
        _workbook(
            "Movimentação",
            header,
            [
                ["Crédito", "01/01/2026", "Compra", "ITSA4 - Itaú", "XP", "2", "10", "20"],
                ["Débito", "02/01/2026", "Venda", "ITSA4 - Itaú", "XP", "1", "12", "12"],
            ],
        )
    )
    assert (purchase.status, purchase.event_type) == (B3RowStatus.NEW, "BUY")
    assert (sale.status, sale.event_type) == (B3RowStatus.NEW, "SELL")


def test_simple_transfer_and_lending_never_become_trades() -> None:
    header = [
        "Entrada/Saída",
        "Data",
        "Movimentação",
        "Produto",
        "Instituição",
        "Quantidade",
        "Preço unitário",
        "Valor",
    ]
    transfer, lending = B3MovementReportParser().parse(
        _workbook(
            "Movimentação",
            header,
            [
                ["Crédito", "01/01/2026", "Transferência", "ITSA4 - Itaú", "XP", "2", "10", "20"],
                ["Débito", "01/01/2026", "Empréstimo", "ITSA4 - Itaú", "XP", "2", "10", "20"],
            ],
        )
    )
    assert transfer.status is B3RowStatus.UNSUPPORTED and transfer.event_type is None
    assert transfer.detail == "CUSTODY_TRANSFER"
    assert lending.status is B3RowStatus.UNSUPPORTED and lending.event_type is None
    assert lending.detail == "STOCK_LOAN"


def test_stock_loan_credit_and_debit_are_non_economic() -> None:
    header = [
        "Entrada/Saída",
        "Data",
        "Movimentação",
        "Produto",
        "Instituição",
        "Quantidade",
        "Preço unitário",
        "Valor",
    ]
    credit, debit = B3MovementReportParser().parse(
        _workbook(
            "Movimentação",
            header,
            [
                [
                    "Crédito",
                    "01/01/2026",
                    "Empréstimo",
                    "BBAS3 - Banco do Brasil",
                    "XP",
                    "2",
                    "10",
                    "20",
                ],
                [
                    "Débito",
                    "02/01/2026",
                    "Empréstimo",
                    "BBAS3 - Banco do Brasil",
                    "XP",
                    "2",
                    "10",
                    "20",
                ],
            ],
        )
    )
    assert (credit.status, credit.event_type, credit.detail) == (
        B3RowStatus.UNSUPPORTED,
        None,
        "STOCK_LOAN",
    )
    assert (debit.status, debit.event_type, debit.detail) == (
        B3RowStatus.UNSUPPORTED,
        None,
        "STOCK_LOAN",
    )
