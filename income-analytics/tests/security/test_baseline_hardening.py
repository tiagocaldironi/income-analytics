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


def test_issue77_review_is_bound_to_public_migration_bytes():
    import hashlib
    import json

    root = Path(__file__).resolve().parents[2]
    inventory = (
        root / "docs/engineering/scoped-financial-certification/immutable_reference_inventory.json"
    )
    content = inventory.read_bytes()
    reference = json.loads(content)["files"]["alembic/versions/0008_paid_income_brapi.py"]
    assert (
        hashlib.sha256(
            (root / "alembic/versions/0008_paid_income_brapi.py").read_bytes()
        ).hexdigest()
        == reference
    )
    policy = json.loads(
        (root / "docs/engineering/security/security_scanner_triage.json").read_text()
    )
    reviewed = next(
        row
        for row in policy["gitleaks_decisions"]
        if row["identity"] == "197358740fcb22d9780a8e416b7586a1cbb820784e86a44d540dcfd7bec243b4"
    )
    assert reviewed["content_sha256"] == hashlib.sha256(content).hexdigest()
    assert reviewed["state"] == "FALSE_POSITIVE" and reviewed["reason"]


@pytest.mark.parametrize("field", ["content_sha256", "file", "line", "rule", "commit"])
def test_issue77_changed_occurrence_has_no_existing_approval(field):
    import hashlib
    import json

    root = Path(__file__).resolve().parents[2]
    policy = json.loads(
        (root / "docs/engineering/security/security_scanner_triage.json").read_text()
    )
    decisions = {row["identity"] for row in policy["gitleaks_decisions"]}
    row = {
        "tool": "gitleaks",
        "mode": "dir",
        "rule": "generic-api-key",
        "file": (
            "income-analytics/docs/engineering/scoped-financial-certification/"
            "immutable_reference_inventory.json"
        ),
        "line": 12,
        "commit": "",
        "state": "POTENTIAL",
        "content_sha256": "d6f99bca05a7d3f6ad4d3e67ce46db5c6876da71dfc7c15d15c5b1b0f7c83853",
    }
    assert hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest() in decisions
    row[field] = 13 if field == "line" else "changed-unreviewed-occurrence"
    assert hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest() not in decisions
