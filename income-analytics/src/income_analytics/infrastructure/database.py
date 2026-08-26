"""Database configuration isolated from the domain."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """SQLAlchemy metadata owned by infrastructure."""


def database_url() -> str:
    path = Path(os.environ.get("INCOME_ANALYTICS_DATABASE", "income_analytics.db"))
    return f"sqlite:///{path.as_posix()}"


engine = create_engine(database_url())
SessionFactory = sessionmaker(bind=engine)


def initialize_database() -> None:
    """Upgrade the configured local database through the migration history."""
    from alembic.config import Config

    from alembic import command

    config = Config(str(Path(__file__).parents[3] / "alembic.ini"))
    if (
        "assets" in inspect(engine).get_table_names()
        and "alembic_version" not in inspect(engine).get_table_names()
    ):
        command.stamp(config, "head")
    command.upgrade(config, "head")
