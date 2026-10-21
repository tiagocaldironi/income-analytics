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


def test_draft_cannot_be_adopted_via_api():
    client = TestClient(app)
    response = client.post(
        "/api/income-starter/models/primeiros-passos/adopt",
        json={"version": 1},
    )

    assert response.status_code == 409
    assert "não foi publicado" in response.json()["detail"]


def test_catalog_has_no_public_review_or_publish_endpoint():
    paths = {route.path for route in app.routes}

    assert not any(
        path.startswith("/api/income-starter/")
        and (path.endswith("/review") or path.endswith("/publish"))
        for path in paths
    )
