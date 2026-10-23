"""Database configuration isolated from the domain."""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """SQLAlchemy metadata owned by infrastructure."""


def database_url() -> str:
    path = Path(os.environ.get("INCOME_ANALYTICS_DATABASE", "income_analytics.db"))
    return f"sqlite:///{path.as_posix()}"


engine = create_engine(database_url())


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(connection, _record) -> None:
    if connection.__class__.__module__.startswith("sqlite3"):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionFactory = sessionmaker(bind=engine)
_migration_lock = RLock()
_initialized_database_path: Path | None = None


def initialize_database() -> None:
    """Upgrade the configured local database through the migration history."""
    global _initialized_database_path
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    from alembic import command

    # Startup refresh tasks and HTTP requests can reach repositories together.
    # Alembic's module-level proxy is not re-entrant, so migrations must be
    # serialized within this local process.
    with _migration_lock:
        config = Config(str(Path(__file__).parents[3] / "alembic.ini"))
        database_path = Path(os.environ.get("INCOME_ANALYTICS_DATABASE", "income_analytics.db"))
        database_path = database_path.resolve()
        if _initialized_database_path == database_path:
            return
        from income_analytics.infrastructure.auth_config import saas_enabled

        if saas_enabled():
            script = ScriptDirectory.from_config(config)
            with engine.connect() as connection:
                revision = MigrationContext.configure(connection).get_current_revision()
            if revision != script.get_current_head():
                raise RuntimeError(
                    "SaaS requires an explicitly migrated database; run reviewed Alembic deployment"
                )
            _initialized_database_path = database_path
            return
        if (
            "assets" in inspect(engine).get_table_names()
            and "alembic_version" not in inspect(engine).get_table_names()
        ):
            command.stamp(config, "head")
        script = ScriptDirectory.from_config(config)
        with engine.connect() as connection:
            current_revision = MigrationContext.configure(connection).get_current_revision()
        target_revision = script.get_current_head()
        if (
            not os.environ.get("INCOME_ANALYTICS_TESTING")
            and database_path.exists()
            and current_revision is not None
            and current_revision != target_revision
        ):
            backups = database_path.parent / "backups"
            backups.mkdir(exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            shutil.copy2(database_path, backups / f"{database_path.stem}-{timestamp}.db")
        command.upgrade(config, "head")
        _initialized_database_path = database_path
