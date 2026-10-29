"""Synthetic configuration and HTTP regressions, without real credentials."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from income_analytics.infrastructure.auth_config import (
    origin,
    saas_enabled,
    validate_configuration,
    validate_database_path,
)
from income_analytics.main import app


@pytest.mark.parametrize("key", ["INCOME_ENV", "ENVIRONMENT"])
@pytest.mark.parametrize("value", ["production", "prod", "PRODUCTION"])
def test_production_alias_cannot_enable_local_mode(monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    monkeypatch.setenv("INCOME_AUTH_MODE", "local")
    with pytest.raises(RuntimeError, match="Firebase"):
        saas_enabled()


def test_remote_local_mode_rejected_even_with_forwarded_loopback(monkeypatch):
    monkeypatch.setenv("INCOME_AUTH_MODE", "local")
    client = TestClient(app, client=("192.0.2.10", 50000))
    response = client.get("/api/portfolio", headers={"X-Forwarded-For": "127.0.0.1"})
    assert response.status_code == 403
    assert "positions" not in response.json()


@pytest.mark.parametrize("address", ["https://user:pass@income.test", "https://income.test/a"])
def test_origin_rejects_userinfo_and_paths(monkeypatch, address):
    monkeypatch.setenv("INCOME_APP_ORIGIN", address)
    with pytest.raises(RuntimeError, match="exact origin"):
        origin()


def test_database_boundary_rejects_traversal_before_open(monkeypatch, tmp_path):
    monkeypatch.setenv("INCOME_DATA_ROOT", str(tmp_path / "data"))
    outside = tmp_path / "outside.db"
    with pytest.raises(RuntimeError, match="outside"):
        validate_database_path(tmp_path / "data" / ".." / "outside.db")
    assert not outside.exists()
    assert validate_database_path(tmp_path / "data" / "portfolio.db").parent == tmp_path / "data"


def test_production_requires_explicit_database_boundary(monkeypatch):
    monkeypatch.setenv("INCOME_ENV", "production")
    monkeypatch.delenv("INCOME_DATA_ROOT", raising=False)
    with pytest.raises(RuntimeError, match="INCOME_DATA_ROOT"):
        validate_database_path(Path("synthetic.db"))


def test_emulator_cannot_override_production_alias(monkeypatch, tmp_path):
    monkeypatch.setenv("INCOME_ENV", "development")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("INCOME_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("INCOME_ANALYTICS_DATABASE", str(tmp_path / "synthetic.db"))
    monkeypatch.setenv("INCOME_AUTH_MODE", "firebase")
    monkeypatch.setenv("INCOME_APP_ORIGIN", "https://income.test")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "demo-synthetic")
    monkeypatch.setenv("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099")
    with pytest.raises(RuntimeError, match="forbidden"):
        validate_configuration()


def test_log_credentials_email_and_exception_are_redacted():
    import logging

    from income_analytics.infrastructure.security_logging import install_log_redaction

    install_log_redaction()
    try:
        raise ValueError("https://provider.invalid/query?apikey=synthetic-value&x=ok")
    except ValueError:
        import sys

        record = logging.getLogRecordFactory()(
            "synthetic",
            logging.ERROR,
            __file__,
            1,
            "Bearer synthetic-bearer someone@example.invalid",
            (),
            sys.exc_info(),
        )
    output = logging.Formatter("%(message)s").format(record)
    assert "synthetic-value" not in output
    assert "synthetic-bearer" not in output
    assert "someone@example.invalid" not in output
    assert "[REDACTED]" in output


def test_local_dns_rebinding_and_cross_site_write_rejected(monkeypatch):
    monkeypatch.setenv("INCOME_AUTH_MODE", "local")
    client = TestClient(app, client=("127.0.0.1", 50000), base_url="http://attacker.invalid")
    assert client.get("/api/portfolio").status_code == 403
    client = TestClient(app, client=("127.0.0.1", 50000), base_url="http://localhost")
    assert (
        client.post(
            "/api/trades", headers={"Origin": "https://attacker.invalid"}, json={}
        ).status_code
        == 403
    )


def test_production_alias_cannot_relax_https(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("INCOME_ENV", "development")
    monkeypatch.setenv("INCOME_APP_ORIGIN", "http://localhost:8002")
    with pytest.raises(RuntimeError, match="HTTPS"):
        origin()


def test_production_relative_data_root_rejected(monkeypatch):
    monkeypatch.setenv("INCOME_ENV", "production")
    monkeypatch.setenv("INCOME_DATA_ROOT", "relative-data")
    with pytest.raises(RuntimeError, match="absolute"):
        validate_database_path(Path("relative-data/synthetic.db"))
