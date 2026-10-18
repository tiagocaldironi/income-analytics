import json
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from income_analytics import main as application_main
from income_analytics.api.routers.dashboard import (
    list_investment_tools,
    magic_formula_stock_detail,
    magic_formula_stocks,
)
from income_analytics.api.routers.dashboard import (
    router as dashboard_router,
)
from income_analytics.application.magic_formula_canonical_ranking import (
    MagicFormulaCanonicalRankingRepository,
    _read_universe,
)


def runtime_api_app() -> FastAPI:
    application = FastAPI()
    application.include_router(dashboard_router)
    return application


@pytest.fixture
def published_point_in_time_ranking(tmp_path, monkeypatch):
    snapshot_path = Path("docs/appendices/magic_formula_v12_2/ranking_snapshot.json")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    repository = MagicFormulaCanonicalRankingRepository(tmp_path / "canonical_rankings.db")
    repository.save(snapshot)
    repository.record_release_event(
        snapshot["ranking_snapshot_id"],
        "PUBLISHED",
        "TEST_POINT_IN_TIME_RELEASE",
        created_at="2026-10-16T12:00:00Z",
    )
    monkeypatch.setattr(
        "income_analytics.api.routers.dashboard.MagicFormulaCanonicalRankingRepository",
        lambda: repository,
    )
    return snapshot


def test_magic_formula_api_reads_persisted_snapshot_and_searches_ticker(
    published_point_in_time_ranking,
) -> None:
    response = magic_formula_stocks(q="WEGE3", page=1, page_size=25)

    assert response["snapshot_available"] is True
    assert response["total"] == 1
    assert response["items"][0]["selected_security"] == "WEGE3"
    assert response["summary"]["ranked"] == 165
    assert response["global_rank_preserved"] is True
    assert response["items"][0]["sector"]
    assert response["items"][0]["sector_source_reference"].startswith(
        "fca_cia_aberta_2025.zip|fca_cia_aberta_geral_2025.csv"
    )


def test_sector_metadata_covers_the_165_ranked_companies_without_changing_hash(
    published_point_in_time_ranking,
) -> None:
    first = magic_formula_stocks(page=1, page_size=100)
    second = magic_formula_stocks(page=2, page_size=100)
    rows = [*first["items"], *second["items"]]

    assert len(rows) == 165
    assert all(row.get("sector") for row in rows)
    assert all(
        row["sector_source_reference"].startswith("fca_cia_aberta_2025.zip|") for row in rows
    )
    assert published_point_in_time_ranking["ranking_snapshot_id"] == "mf-f1ee50809c83979ba221d84e"
    assert (
        published_point_in_time_ranking["ranking_hash"]
        == json.loads(
            Path("docs/appendices/magic_formula_v12_2/ranking_snapshot.json").read_text(
                encoding="utf-8"
            )
        )["ranking_hash"]
    )


def test_tools_catalog_marks_available_magic_formula_as_partial(
    published_point_in_time_ranking,
) -> None:
    tools = list_investment_tools()["items"]

    assert tools[0]["status"] == "PARTIAL"
    assert tools[0]["version"] == "MF_BR_2027_V1"


def test_magic_formula_company_detail_returns_source_provenance(
    published_point_in_time_ranking,
) -> None:
    listed = magic_formula_stocks(q="WEGE3", page=1, page_size=25)
    company_id = listed["items"][0]["company_id"]

    detail = magic_formula_stock_detail(
        company_id, snapshot_id=listed["snapshot"]["ranking_snapshot_id"]
    )

    assert detail["item"]["selected_security"] == "WEGE3"
    assert detail["provenance"]["filing_date"] <= "2025-12-30"
    assert detail["provenance"]["selected_security_source"]["price_source_reference"].startswith(
        "COTAHIST"
    )
    assert detail["snapshot"]["ranking_snapshot_id"] == listed["snapshot"]["ranking_snapshot_id"]
    assert detail["company"]["ticker"] == listed["items"][0]["selected_security"]
    assert detail["company"]["sector"] == listed["items"][0]["sector"]
    assert detail["company"]["sector_point_in_time_safe"] == "UNKNOWN"
    assert detail["company"]["listing_segment"] is None
    assert detail["ranking"]["global_rank"] == listed["items"][0]["global_rank"]
    assert detail["calculation"]["ebit"] == listed["items"][0]["ebit"]
    assert detail["calculation"]["enterprise_value"] == listed["items"][0]["enterprise_value"]
    assert detail["calculation"]["cash"] is not None
    assert detail["calculation"]["debt"] is not None
    assert detail["calculation"]["value_types"]["enterprise_value"] == "DERIVED"
    assert detail["calculation"]["lineage"]["enterprise_value"]["accounting_sources"]
    assert detail["data_basis"]["financial_reference_period"] == "2024-12-31"
    assert detail["data_basis"]["price_date"] == "2025-12-30"


def test_detail_does_not_build_a_company_outside_the_requested_snapshot(
    published_point_in_time_ranking,
) -> None:
    with pytest.raises(HTTPException) as error:
        magic_formula_stock_detail("missing-company", snapshot_id="mf-f1ee50809c83979ba221d84e")
    assert getattr(error.value, "status_code", None) == 404


def test_csna3_has_no_detail_when_it_is_blocked_from_the_published_ranking(
    published_point_in_time_ranking,
) -> None:
    listed = magic_formula_stocks(q="CSNA3", page=1, page_size=25)

    assert listed["total"] == 0
    assert all(row["selected_security"] != "CSNA3" for row in listed["items"])
    blocked = next(
        row for row in published_point_in_time_ranking["blocked"] if row["ticker"] == "CSNA3"
    )
    source = _read_universe(
        Path("data/magic_formula/universe_snapshots.db"),
        published_point_in_time_ranking["data_snapshot_id"],
    )
    assert blocked["status"] == "ELIGIBLE_DATA_BLOCKED"
    csna3 = next(issuer for issuer in source["issuers"] if issuer["cvm_code"] == "004030")
    with pytest.raises(HTTPException) as error:
        magic_formula_stock_detail(
            csna3["issuer_id"],
            snapshot_id=published_point_in_time_ranking["ranking_snapshot_id"],
        )
    assert error.value.status_code == 404


def test_runtime_http_endpoint_returns_the_published_point_in_time_contract(
    published_point_in_time_ranking,
) -> None:
    response = TestClient(runtime_api_app()).get(
        "/api/tools/magic-formula/stocks?page=1&page_size=25"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "AVAILABLE"
    assert body["methodology_version"] == "MF_BR_2027_V1"
    assert body["snapshot"]["ranking_snapshot_id"] == "mf-f1ee50809c83979ba221d84e"
    assert body["summary"]["ranked"] == 165
    assert body["total"] == 165
    assert len(body["items"]) == 25
    assert body["items"][0]["global_rank"] == 1


def test_runtime_http_endpoint_reports_missing_published_snapshot_explicitly(
    tmp_path, monkeypatch
) -> None:
    repository = MagicFormulaCanonicalRankingRepository(tmp_path / "empty-rankings.db")
    monkeypatch.setattr(
        "income_analytics.api.routers.dashboard.MagicFormulaCanonicalRankingRepository",
        lambda: repository,
    )

    response = TestClient(runtime_api_app()).get("/api/tools/magic-formula/stocks")

    assert response.status_code == 200
    assert response.json() == {
        "tool": "MAGIC_FORMULA_STOCKS",
        "methodology_version": "MF_BR_2027_V1",
        "status": "NO_PUBLISHED_RANKING",
        "snapshot_available": False,
        "items": [],
        "total": 0,
        "page": 1,
    }


def test_startup_keeps_other_routes_available_when_portfolio_projection_is_invalid(
    monkeypatch, caplog
) -> None:
    def fail_rebuild() -> None:
        raise ValueError("Cannot sell more than the current position quantity.")

    class InertThread:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def start(self) -> None:
            pass

    monkeypatch.setattr(
        application_main,
        "ensure_portfolio_dashboard_snapshot_current",
        fail_rebuild,
    )
    monkeypatch.setattr(application_main, "Thread", InertThread)
    monkeypatch.setattr(application_main, "run_daily_market_data_refresh", lambda: None)
    monkeypatch.setattr(application_main, "run_daily_recurring_rule_execution", lambda: None)
    monkeypatch.setattr(application_main, "run_daily_paid_income_sync", lambda: None)
    monkeypatch.setattr(application_main, "run_reference_data_bootstrap", lambda: None)
    monkeypatch.setattr(application_main, "run_scheduled_historical_market_refresh", lambda: None)

    application_main.start_daily_data_refresh()

    assert "continuing with the last persisted projection" in caplog.text


def test_controlled_runtime_can_disable_startup_background_jobs(monkeypatch) -> None:
    class UnexpectedThread:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("Background job thread must not start in controlled mode")

    monkeypatch.setenv("INCOME_ANALYTICS_DISABLE_BACKGROUND_JOBS", "1")
    monkeypatch.setattr(application_main, "ensure_portfolio_dashboard_snapshot_current", lambda: {})
    monkeypatch.setattr(application_main, "Thread", UnexpectedThread)

    application_main.start_daily_data_refresh()
