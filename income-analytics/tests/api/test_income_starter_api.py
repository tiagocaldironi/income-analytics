from fastapi.testclient import TestClient

from income_analytics.main import app


def test_catalog_exposes_four_drafts_without_allocations():
    response = TestClient(app).get("/api/income-starter/catalog")

    assert response.status_code == 200
    models = response.json()["models"]
    assert {model["name"] for model in models} == {
        "Primeiros Passos",
        "Conservadora",
        "Moderada",
        "Arrojada",
    }
    assert {model["status"] for model in models} == {"DRAFT"}
    assert all(model["allocations"] is None for model in models)
    assert all(model["adoption_available"] is False for model in models)
    by_name = {model["name"]: model for model in models}
    assert by_name["Primeiros Passos"]["template_type"] == "GUIDED_JOURNEY"
    assert all(
        by_name[name]["template_type"] == "ALLOCATION_MODEL"
        for name in {"Conservadora", "Moderada", "Arrojada"}
    )


def test_draft_cannot_be_adopted_via_api():
    client = TestClient(app)
    response = client.post(
        "/api/income-starter/models/primeiros-passos/adopt",
        json={"version": 1},
    )

    assert response.status_code == 409
    assert "não podem ser adotadas" in response.json()["detail"]


def test_catalog_has_no_public_review_or_publish_endpoint():
    paths = set(app.openapi()["paths"])

    assert not any(
        path.startswith("/api/income-starter/")
        and (path.endswith("/review") or path.endswith("/publish"))
        for path in paths
    )


def test_reserve_journey_read_is_self_declared_and_portfolio_scoped():
    response = TestClient(app).get("/api/income-starter/journey/reserve")

    assert response.status_code == 200
    assert response.json()["value_source"] == "SELF_DECLARED"
    assert response.json()["portfolio_id"]
