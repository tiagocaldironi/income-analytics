"""A real isolated migration and explicit owner binding never rewrites the ledger."""

import importlib.util
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "bind_legacy", ROOT / "scripts/bind_legacy_portfolio.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_binding_dry_run_backup_idempotence_and_ledger_preservation(tmp_path):
    path = tmp_path / "legacy.db"
    env = dict(
        os.environ,
        INCOME_ANALYTICS_DATABASE=str(path),
        INCOME_AUTH_MODE="local",
        PYTHONPATH=str(ROOT / "src"),
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
    )
    wallet, owner, actor = str(uuid4()), str(uuid4()), str(uuid4())
    with closing(sqlite3.connect(path)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executemany("INSERT INTO users(id,status) VALUES (?,'ACTIVE')", [(owner,), (actor,)])
        db.execute(
            "INSERT INTO auth_identities(id,user_id,issuer,subject,"
            "approved_methods,link_confirmed_until) "
            "VALUES (?,?,'https://securetoken.google.com/demo-test','expected-uid','[\"password\"]',0)",
            (str(uuid4()), owner),
        )
        db.execute(
            "INSERT INTO portfolios(id,name,base_currency,status,created_at,updated_at) "
            "VALUES (?, 'Legacy','BRL','ACTIVE',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
            (wallet,),
        )
        db.execute(
            "INSERT INTO financial_events(id,portfolio_id,account_id,event_type,amount,"
            "effective_date,occurred_at,registered_at,description) "
            "VALUES (?,?,?,'DEPOSIT','100','2026-01-01',"
            "CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,'Legacy')",
            (str(uuid4()), wallet, str(uuid4())),
        )
        db.commit()
        before = db.execute("SELECT * FROM financial_events").fetchall()
    arguments = dict(
        database=path,
        portfolio_id=wallet,
        owner_id=owner,
        firebase_uid="expected-uid",
        project_id="demo-test",
        actor=actor,
        reason="Private approved change ABC",
    )
    assert module.bind_legacy(**arguments)["status"] == "dry_run_ready"
    with closing(sqlite3.connect(path)) as db:
        assert db.execute(
            "SELECT owner_user_id FROM portfolios WHERE id=?", (wallet,)
        ).fetchone() == (None,)
    with pytest.raises(ValueError):
        module.bind_legacy(**arguments, apply=True)
    result = module.bind_legacy(
        **arguments, apply=True, maintenance=True, backup_directory=tmp_path / "backups"
    )
    assert result["status"] == "bound"
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("SELECT * FROM financial_events").fetchall() == before
        assert db.execute("SELECT actor_id,evidence_ref FROM security_audit").fetchone()[0] == actor
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    with closing(sqlite3.connect(result["backup"])) as backup:
        assert backup.execute(
            "SELECT owner_user_id FROM portfolios WHERE id=?", (wallet,)
        ).fetchone() == (None,)
        assert backup.execute("SELECT * FROM financial_events").fetchall() == before
    assert module.bind_legacy(**arguments)["status"] == "already_owned"
    with pytest.raises(ValueError):
        module.bind_legacy(**{**arguments, "firebase_uid": "wrong-uid"})
