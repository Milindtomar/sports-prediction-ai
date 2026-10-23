"""SQLModel engine/session. SQLite for local dev, PostgreSQL in production (DATABASE_URL)."""
from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args, pool_pre_ping=True)


def _add_missing_columns() -> None:
    """Lightweight forward migration: create_all() never alters existing tables, so add new nullable
    columns to databases created by an earlier version (SQLite and PostgreSQL)."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                ddl = col.type.compile(dialect=engine.dialect)
                default = " DEFAULT 0" if ddl.upper().startswith(("BOOL", "INT")) and not col.nullable else (" DEFAULT ''" if ddl.upper().startswith(("VARCHAR", "TEXT", "AUTOSTR")) and not col.nullable else "")
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl}{default}'))


def init_db() -> None:
    from app import models_db  # noqa: F401  (register tables)
    SQLModel.metadata.create_all(engine)
    _add_missing_columns()


def get_session():
    with Session(engine) as session:
        yield session
