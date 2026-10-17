"""Public API contract for the auditable B3 import flow.

These tests intentionally exercise the HTTP boundary: the spreadsheet never
calls the legacy per-operation endpoints and an ``apply`` always refers to a
previously reviewed batch.
"""

from __future__ import annotations

import asyncio
import json
from base64 import b64encode
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from income_analytics.api.routers import dashboard
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.main import app


def _xlsx_with_rows(
    headers: list[str], rows: list[list[str]], sheet_name: str = "Negociações"
) -> str:
    """Build a tiny XLSX with inline strings, without a test-only dependency."""

    def cell(column: int, row: int, value: str) -> str:
        letter = ""
        current = column
        while current:
            current, remainder = divmod(current - 1, 26)
            letter = chr(65 + remainder) + letter
        escaped = value.replace("&", "&amp;").replace("<", "&lt;")
        return f'<c r="{letter}{row}" t="inlineStr"><is><t>{escaped}</t></is></c>'

    all_rows = [headers, *rows]
    sheet_rows = "".join(
        '<row r="%s">%s</row>'
        % (index, "".join(cell(column, index, value) for column, value in enumerate(row, 1)))
        for index, row in enumerate(all_rows, 1)
    )
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{sheet_rows}</sheetData></worksheet>"
    )
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as package:
        package.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" '
            'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>",
        )
        package.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        package.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        package.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        package.writestr("xl/worksheets/sheet1.xml", worksheet)
    return b64encode(archive.getvalue()).decode("ascii")


def _trade_workbook() -> str:
    return _xlsx_with_rows(
        [
            "Data do Negócio",
            "Tipo de Movimentação",
            "Mercado",
            "Instituição",
            "Código de Negociação",
            "Quantidade",
            "Preço",
            "Valor",
        ],
        [
            [
                "02/01/2026",
                "Compra",
                "Mercado Fracionário",
                "Corretora X",
                "ITSA4F",
                "10",
                "11,50",
                "115,00",
            ]
        ],
    )


def _trades(rows: list[list[str]]) -> str:
    return _xlsx_with_rows(
        [
            "Data do Negócio",
            "Tipo de Movimentação",
            "Mercado",
            "Instituição",
            "Código de Negociação",
            "Quantidade",
            "Preço",
            "Valor",
        ],
        rows,
    )


def _post_json(path: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    """Exercise the FastAPI ASGI boundary without a test-only HTTP client."""

    body = json.dumps(payload).encode("utf-8")
    sent: list[dict[str, object]] = []
    received = False

    async def receive() -> dict[str, object]:
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    async def request() -> None:
        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": path,
                "raw_path": path.encode("ascii"),
                "query_string": b"",
                "headers": [(b"content-type", b"application/json")],
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
                "root_path": "",
            },
            receive,
            send,
        )

    asyncio.run(request())
    status = next(message["status"] for message in sent if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"") for message in sent if message["type"] == "http.response.body"
    )
    return int(status), json.loads(response_body or b"{}")


def _ensure_itsa4() -> None:
    """Seed the normal security master in the isolated test database."""
    if "ITSA4" not in dashboard.session._assets:
        dashboard.session.register_asset(
            ticker="ITSA4",
            name="Itaúsa",
            asset_class=AssetClass.BRAZILIAN_STOCK,
            country="BR",
            currency_code="BRL",
        )


def _ensure_gap3() -> None:
    if "GAP3" not in dashboard.session._assets:
        dashboard.session.register_asset(
            ticker="GAP3",
            name="Dados incompletos",
            asset_class=AssetClass.BRAZILIAN_STOCK,
            country="BR",
            currency_code="BRL",
        )


def test_b3_preview_creates_an_auditable_batch_and_normalizes_fractional_symbol() -> None:
    _ensure_itsa4()
    status, preview = _post_json(
        "/imports/b3/preview",
        {
            "workbook_base64": _trade_workbook(),
            "file_name": "negociacao-b3.xlsx",
            "report_type": "NEGOTIATION",
        },
    )

    assert status == 200, preview
    assert preview["batch_id"]
    assert preview["status"] == "PREVIEWED"
    assert preview["file_name"] == "negociacao-b3.xlsx"
    assert preview["report_type"] == "NEGOTIATION"
    assert preview["counts"] == {
        "total": 1,
        "new": 1,
        "duplicate": 0,
        "review_required": 0,
        "unsupported": 0,
        "invalid": 0,
    }
    item = preview["items"][0]
    assert item["status"] == "NEW"
    assert item["source_symbol"] == "ITSA4F"
    assert item["normalized_symbol"] == "ITSA4"
    assert item["institution"] == "Corretora X"
    assert item["market"] == "Mercado Fracionário"
    assert item["occurrence_index"] == 1


def test_b3_preview_is_read_only() -> None:
    import os
    import sqlite3

    _ensure_itsa4()
    with sqlite3.connect(os.environ["INCOME_ANALYTICS_DATABASE"]) as connection:
        before = tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("financial_events", "b3_import_batches", "b3_imported_records")
        )
    status, preview = _post_json(
        "/imports/b3/preview",
        {
            "workbook_base64": _trade_workbook(),
            "file_name": "read-only.xlsx",
            "report_type": "NEGOTIATION",
        },
    )
    assert status == 200, preview
    with sqlite3.connect(os.environ["INCOME_ANALYTICS_DATABASE"]) as connection:
        after = tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("financial_events", "b3_import_batches", "b3_imported_records")
        )
    assert after == before


def test_b3_apply_requires_a_previewed_batch_and_is_idempotent() -> None:
    _ensure_itsa4()
    preview_status, preview = _post_json(
        "/imports/b3/preview",
        {
            "workbook_base64": _trade_workbook(),
            "file_name": "negociacao-b3.xlsx",
            "report_type": "NEGOTIATION",
        },
    )
    assert preview_status == 200, preview
    batch_id = preview["batch_id"]

    applied_status, applied = _post_json(f"/imports/b3/{batch_id}/apply", {})
    assert applied_status == 200, applied
    assert applied["batch_id"] == batch_id
    assert applied["status"] == "APPLIED"
    assert applied["applied_count"] == 1

    repeated_status, repeated = _post_json(f"/imports/b3/{batch_id}/apply", {})
    assert repeated_status == 200, repeated
    assert repeated["batch_id"] == batch_id
    assert repeated["applied_count"] == 0
    assert repeated["duplicate_count"] == 1


def test_b3_preview_rejects_missing_required_column_with_an_explicit_reason() -> None:
    workbook = _xlsx_with_rows(
        ["Data do Negócio", "Tipo de Movimentação", "Mercado", "Código de Negociação"],
        [["02/01/2026", "Compra", "Mercado à Vista", "ITSA4"]],
    )
    status, response = _post_json(
        "/imports/b3/preview",
        {
            "workbook_base64": workbook,
            "file_name": "layout-invalido.xlsx",
            "report_type": "NEGOTIATION",
        },
    )

    assert status == 422, response
    assert "INVALID_B3_LAYOUT" in str(response)


def test_overlapping_and_identical_operations_are_idempotent_after_apply() -> None:
    _ensure_itsa4()

    def preview_apply(book: str) -> dict[str, object]:
        _, preview = _post_json(
            "/imports/b3/preview",
            {"workbook_base64": book, "file_name": "negociacao.xlsx", "report_type": "NEGOTIATION"},
        )
        _, applied = _post_json(f"/imports/b3/{preview['batch_id']}/apply", {})
        return applied

    x = ["01/06/2026", "Compra", "Mercado à Vista", "XP", "ITSA4", "1", "10", "10"]
    y = ["02/06/2026", "Compra", "Mercado à Vista", "XP", "ITSA4", "1", "11", "11"]
    z = ["03/06/2026", "Compra", "Mercado à Vista", "XP", "ITSA4", "1", "12", "12"]
    w = ["04/06/2026", "Compra", "Mercado à Vista", "XP", "ITSA4", "1", "13", "13"]
    assert preview_apply(_trades([x, y, z]))["applied_count"] == 3
    assert preview_apply(_trades([y, z, w]))["applied_count"] == 1
    identical = ["05/06/2026", "Compra", "Mercado à Vista", "XP", "ITSA4", "1", "14", "14"]
    assert preview_apply(_trades([identical, identical]))["applied_count"] == 2
    assert preview_apply(_trades([identical, identical]))["applied_count"] == 0


def test_apply_filters_every_non_new_status_with_database_readback() -> None:
    _ensure_itsa4()
    import os
    import sqlite3

    with sqlite3.connect(os.environ["INCOME_ANALYTICS_DATABASE"]) as connection:
        events_before = connection.execute("SELECT COUNT(*) FROM financial_events").fetchone()[0]
    headers = [
        "Entrada/Saída",
        "Data",
        "Movimentação",
        "Produto",
        "Instituição",
        "Quantidade",
        "Preço unitário",
        "Valor",
    ]

    def preview(rows: list[list[str]]) -> dict[str, object]:
        status, result = _post_json(
            "/imports/b3/preview",
            {
                "workbook_base64": _xlsx_with_rows(headers, rows, "Movimentações"),
                "file_name": "movimentacao.xlsx",
                "report_type": "MOVEMENT",
            },
        )
        assert status == 200, result
        return result

    duplicate_source = ["01/01/2026", "Compra", "Mercado à Vista", "XP", "ITSA4", "1", "10", "10"]
    first_status, first = _post_json(
        "/imports/b3/preview",
        {
            "workbook_base64": _trades([duplicate_source]),
            "file_name": "negociacao.xlsx",
            "report_type": "NEGOTIATION",
        },
    )
    assert first_status == 200, first
    assert _post_json(f"/imports/b3/{first['batch_id']}/apply", {})[1]["applied_count"] == 1
    mixed = preview(
        [
            [
                "Crédito",
                "01/01/2026",
                "Transferência - Liquidação",
                "ITSA4 - Itausa",
                "XP",
                "1",
                "10",
                "10",
            ],
            [
                "Crédito",
                "02/01/2026",
                "Transferência - Liquidação",
                "ITSA4 - Itausa",
                "XP",
                "1",
                "11",
                "11",
            ],
            ["Crédito", "03/01/2026", "Rendimento", "ITSA4 - Itausa", "XP", "1", "1", "1"],
            ["Crédito", "04/01/2026", "Transferência", "ITSA4 - Itausa", "XP", "1", "1", "1"],
            ["Crédito", "", "Dividendo", "ITSA4 - Itausa", "XP", "1", "1", ""],
        ]
    )
    assert mixed["counts"] == {
        "total": 5,
        "new": 1,
        "duplicate": 1,
        "review_required": 1,
        "unsupported": 1,
        "invalid": 1,
    }
    _, applied = _post_json(f"/imports/b3/{mixed['batch_id']}/apply", {})
    assert applied["applied_count"] == 1
    with sqlite3.connect(os.environ["INCOME_ANALYTICS_DATABASE"]) as connection:
        # One negotiation trade was applied before the movement batch, which
        # then applies only its one distinct, fully-priced settlement trade.
        assert (
            connection.execute("SELECT COUNT(*) FROM financial_events").fetchone()[0]
            == events_before + 2
        )


def test_settlement_sell_with_data_gap_stays_review_required() -> None:
    import os
    import sqlite3

    _ensure_gap3()
    headers = [
        "Entrada/Saída",
        "Data",
        "Movimentação",
        "Produto",
        "Instituição",
        "Quantidade",
        "Preço unitário",
        "Valor",
    ]
    rows = [
        [
            "Crédito",
            "01/07/2026",
            "Transferência - Liquidação",
            "GAP3 - Teste",
            "XP",
            "50",
            "10",
            "500",
        ],
        [
            "Débito",
            "02/07/2026",
            "Transferência - Liquidação",
            "GAP3 - Teste",
            "XP",
            "31",
            "-",
            "-",
        ],
    ]
    status, preview = _post_json(
        "/imports/b3/preview",
        {
            "workbook_base64": _xlsx_with_rows(headers, rows, "Movimentações"),
            "file_name": "gap.xlsx",
            "report_type": "MOVEMENT",
        },
    )
    assert status == 200, preview
    assert preview["items"][1]["status"] == "REVIEW_REQUIRED"
    assert preview["items"][1]["quantity_status"] == "OBSERVED"
    assert preview["items"][1]["financial_status"] == "DATA_GAP"
    _, applied = _post_json(f"/imports/b3/{preview['batch_id']}/apply", {})
    assert applied["applied_count"] == 1
    with sqlite3.connect(os.environ["INCOME_ANALYTICS_DATABASE"]) as connection:
        sell = connection.execute(
            "SELECT quantity, unit_price, amount, metadata_json FROM financial_events "
            "WHERE event_type = 'SELL' AND effective_date = '2026-07-02'"
        ).fetchone()
    assert sell is None
