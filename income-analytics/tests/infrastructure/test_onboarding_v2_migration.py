import os
import sqlite3
import subprocess
import sys


def test_onboarding_v2_migration_preserves_old_tables_and_skip(tmp_path):
    path = tmp_path / "onboarding-migration.db"
    env = {**os.environ, "INCOME_ANALYTICS_DATABASE": str(path), "INCOME_ANALYTICS_TESTING": "1"}

    def migrate(target):
        return subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", target],
            env=env,
            capture_output=True,
            text=True,
        )

    result = migrate("0026_portfolio_onboarding")
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(path) as db:
        wallet = db.execute("SELECT id FROM portfolios LIMIT 1").fetchone()[0]
        db.execute(
            "INSERT INTO portfolio_onboarding "
            "(viewer_key,portfolio_id,current_step,status,updated_at) "
            "VALUES ('local',?,3,'SKIPPED',12)",
            (wallet,),
        )
        tables = [
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name!='alembic_version'"
            )
        ]
        before = {name: db.execute('SELECT * FROM "' + name + '"').fetchall() for name in tables}
    result = migrate("head")
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(path) as db:
        assert db.execute("pragma integrity_check").fetchone()[0] == "ok"
        assert not db.execute("pragma foreign_key_check").fetchall()
        assert (
            db.execute(
                "SELECT status FROM onboarding_journeys_v2 WHERE viewer_key='local'"
            ).fetchone()[0]
            == "SKIPPED"
        )
        for name, rows in before.items():
            assert db.execute('SELECT * FROM "' + name + '"').fetchall() == rows, name
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "0026_portfolio_onboarding"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "Preserve contextual onboarding data" in result.stderr
