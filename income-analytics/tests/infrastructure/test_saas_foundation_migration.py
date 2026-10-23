"""Exercise actual Alembic upgrades/rollback on isolated SQLite files only."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[2]
OLD = "0023_income_starter_guided_journey"


def migrate(path, *arguments):
    env = dict(os.environ, INCOME_ANALYTICS_DATABASE=str(path))
    env["PYTHONPATH"] = str(ROOT / "src")
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def snapshot(connection):
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version' ORDER BY name"
    )
    return {name: connection.execute(f'SELECT * FROM "{name}"').fetchall() for (name,) in tables}


def test_upgrade_preserves_legacy_and_downgrade_roundtrip(tmp_path):
    path = tmp_path / "migration.db"
    migrate(path, "upgrade", OLD)
    with sqlite3.connect(path) as db:
        for name in ("A1", "A2", "B1", "B2"):
            db.execute(
                "INSERT INTO portfolios (id,name,base_currency,status,created_at,updated_at) "
                "VALUES (?,?,'BRL','ACTIVE',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
                (str(uuid4()), name),
            )
        db.commit()
        before = snapshot(db)
    migrate(path, "upgrade", "head")
    migrate(path, "upgrade", "head")
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        after = snapshot(db)
        for table, rows in before.items():
            actual = after[table]
            if table == "portfolios":
                assert all(row[-1] is None for row in actual)
                actual = [row[:-1] for row in actual]
            assert actual == rows
        assert not after["users"] and not after["auth_identities"]
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE portfolios SET owner_user_id='missing'")
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    migrate(path, "downgrade", OLD)
    with sqlite3.connect(path) as db:
        assert snapshot(db) == before


def test_identity_constraints_and_rollback_refuses_data_loss(tmp_path):
    path = tmp_path / "identity.db"
    migrate(path, "upgrade", "head")
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        a, b = str(uuid4()), str(uuid4())
        db.executemany("INSERT INTO users(id) VALUES (?)", [(a,), (b,)])
        db.execute("INSERT INTO auth_identities VALUES (?,?,?,?)", (str(uuid4()), a, "idp", "sub"))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO auth_identities VALUES (?,?,?,?)", (str(uuid4()), b, "idp", "sub")
            )
        db.commit()
    with pytest.raises(subprocess.CalledProcessError):
        migrate(path, "downgrade", OLD)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM users").fetchone()[0] == 2
        assert db.execute("SELECT count(*) FROM auth_identities").fetchone()[0] == 1
