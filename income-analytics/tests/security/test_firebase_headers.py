"""Google popup bootstrap must be compatible with our restrictive CSP."""

from fastapi.testclient import TestClient
from income_analytics.main import app


def test_google_bootstrap_allowed_without_relaxing_other_directives(monkeypatch):
    monkeypatch.setenv("INCOME_AUTH_MODE", "firebase")
    monkeypatch.setenv("INCOME_APP_ORIGIN", "http://localhost:8002")
    monkeypatch.setenv("INCOME_ENV", "development")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "demo-header-test")
    with TestClient(app, base_url="http://localhost:8002") as client:
        response = client.get("/entrar")
    assert response.status_code == 200
    csp = dict(
        item.strip().split(" ", 1)
        for item in response.headers["Content-Security-Policy"].split(";")
        if item.strip()
    )
    assert "https://apis.google.com" in csp["script-src"].split()
    assert "'unsafe-inline'" not in csp["script-src"]
    assert "'unsafe-eval'" not in csp["script-src"]
    assert "*" not in csp["script-src"].split()
    assert csp["object-src"] == "'none'"
    assert csp["frame-ancestors"] == "'none'"
