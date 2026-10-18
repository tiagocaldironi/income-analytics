from datetime import date
from decimal import Decimal

import pytest

from income_analytics.application.market_data import MarketDataUnavailable, MarketPriceObservation
from income_analytics.infrastructure.b3_etf_market_data import B3EtfPriceProvider


def test_bdi_layout_maps_fixed_income_etf_category_without_ticker_special_case() -> None:
    provider = B3EtfPriceProvider()
    provider._request_table = lambda _day: {  # type: ignore[method-assign]
        "table": {
            "columns": [
                {"name": "Code"},
                {"name": "Company"},
                {"name": "Opening"},
                {"name": "Minimum"},
                {"name": "Maximum"},
                {"name": "Average"},
                {"name": "Last"},
                {"name": "D1ReferencePrice"},
            ],
            "values": [
                [
                    "AUPO11",
                    "ETF renda fixa A",
                    "111,00",
                    "110,00",
                    "112,00",
                    "111,50",
                    "112,34",
                    "112,00",
                ],
                [
                    "FIXA11",
                    "ETF renda fixa B",
                    "17,00",
                    "17,00",
                    "17,50",
                    "17,20",
                    "17,38",
                    "17,33",
                ],
                ["AREA11", "sem negócio", "-", "-", "-", "-", "-", "17,00"],
            ],
        }
    }

    prices = provider._prices_for_date(date(2026, 10, 6))

    assert prices == {"AUPO11": Decimal("112.34"), "FIXA11": Decimal("17.38")}


def test_bdi_current_price_keeps_reference_date_and_provenance() -> None:
    provider = B3EtfPriceProvider()
    day = date.today()
    provider._request_table = lambda _day: {  # type: ignore[method-assign]
        "table": {
            "columns": [
                {"name": "Code"},
                *({"name": str(i)} for i in range(1, 6)),
                {"name": "Last"},
            ],
            "values": [["BDAP11", "", "", "", "", "", "99.10"]],
        }
    }

    observation = provider.latest_price("bdap11")

    expected = MarketPriceObservation(
        symbol="BDAP11",
        price=Decimal("99.10"),
        currency_code="BRL",
        effective_date=day,
        source="b3_etf",
        retrieved_at=observation.retrieved_at,
    )
    assert observation == expected


def test_bdi_historical_lookup_never_uses_quote_after_requested_date() -> None:
    provider = B3EtfPriceProvider()
    requested = date(2026, 9, 1)
    provider._request_table = lambda _day: {  # type: ignore[method-assign]
        "table": {
            "columns": [
                {"name": "Code"},
                *({"name": str(i)} for i in range(1, 6)),
                {"name": "Last"},
            ],
            "values": [["AUPO11", "", "", "", "", "", "110.50"]],
        }
    }

    observation = provider.price_on("AUPO11", requested)

    assert observation.effective_date == requested
    assert observation.price == Decimal("110.50")


def test_bdi_provider_does_not_invent_price_for_missing_asset() -> None:
    provider = B3EtfPriceProvider()
    provider._request_table = lambda _day: {
        "table": {
            "columns": [
                {"name": "Code"},
                *({"name": str(i)} for i in range(1, 6)),
                {"name": "Last"},
            ],
            "values": [],
        }
    }  # type: ignore[method-assign]

    with pytest.raises(MarketDataUnavailable):
        provider.latest_price("UNKNOWN11")


def test_bdi_batch_reads_multiple_etfs_from_one_daily_table():
    provider = B3EtfPriceProvider()
    day = date.today()
    calls = []

    def read_table(requested_day):
        calls.append(requested_day)
        return {
            "table": {
                "columns": [
                    {"name": name}
                    for name in (
                        "Codigo",
                        "Empresa",
                        "Abertura",
                        "Minimo",
                        "Maximo",
                        "Medio",
                        "Ultimo",
                    )
                ],
                "values": [
                    ["AUPO11", "ETF A", "", "", "", "", "112,34"],
                    ["FIXA11", "ETF B", "", "", "", "", "17,38"],
                ],
            }
        }

    provider._request_table = read_table  # type: ignore[method-assign]

    results = provider.latest_prices(("AUPO11", "FIXA11"))

    assert set(results) == {"AUPO11", "FIXA11"}
    assert results["AUPO11"].price == Decimal("112.34")
    assert results["FIXA11"].price == Decimal("17.38")
    assert calls == [day]


def test_bdi_request_uses_official_structured_endpoint_and_post(monkeypatch):
    from income_analytics.infrastructure import b3_etf_market_data

    provider = B3EtfPriceProvider()
    observed = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"table":{"columns":[],"values":[]}}'

    def fake_urlopen(request, timeout):
        observed["url"] = request.full_url
        observed["method"] = request.method
        observed["body"] = request.data
        observed["timeout"] = timeout
        return Response()

    monkeypatch.setattr(b3_etf_market_data, "urlopen", fake_urlopen)

    provider._request_table(date(2026, 10, 6))

    assert observed == {
        "url": "https://arquivos.b3.com.br/bdi/table/DebenturesBusiness/2026-10-06/2026-10-06/1/1000",
        "method": "POST",
        "body": b"{}",
        "timeout": 8,
    }


def test_bdi_real_layout_uses_ticker_and_last_trade_columns():
    provider = B3EtfPriceProvider()
    provider._request_table = lambda _day: {  # type: ignore[method-assign]
        "table": {
            "columns": [
                {"name": name}
                for name in (
                    "RptDt",
                    "TckrSymb",
                    "Company",
                    "Opening",
                    "Minimum",
                    "Maximum",
                    "Average",
                    "Final",
                    "ClosRefPric",
                    "PurchaseOffer",
                    "SaleOffer",
                    "Quant",
                    "Neg",
                    "Volume",
                )
            ],
            "values": [
                [
                    "06/10/2026",
                    "AUPO11",
                    "BTGP AUPO F11",
                    "106,18",
                    "106,06",
                    "106,56",
                    "106,33",
                    "106,54",
                    "106,11",
                    "106,48",
                    "106,54",
                    "50114",
                    "670",
                    "5328822,77",
                ]
            ],
        }
    }

    assert provider._prices_for_date(date(2026, 10, 6)) == {"AUPO11": Decimal("106.54")}


def test_bdi_history_returns_historical_closes_for_observed_business_days() -> None:
    provider = B3EtfPriceProvider()
    calls = []
    values = {
        date(2026, 9, 29): "111.05",
        date(2026, 9, 30): "111.12",
    }

    def read_table(day):
        calls.append(day)
        rows = [["AUPO11", values[day]]] if day in values else []
        return {
            "table": {
                "columns": [{"name": "TckrSymb"}, {"name": "Final"}],
                "values": rows,
            }
        }

    provider._request_table = read_table  # type: ignore[method-assign]
    observations = provider.history(
        "AUPO11", start_date=date(2026, 9, 28), end_date=date(2026, 9, 30)
    )

    assert [(item.effective_date, item.price, item.source) for item in observations] == [
        (date(2026, 9, 29), Decimal("111.05"), "b3_etf"),
        (date(2026, 9, 30), Decimal("111.12"), "b3_etf"),
    ]
    assert calls == [date(2026, 9, 28), date(2026, 9, 29), date(2026, 9, 30)]
