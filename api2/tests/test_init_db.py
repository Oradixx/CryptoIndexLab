"""Tests for the database initialization run at startup."""

from dataclasses import replace

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import StaticPool

from src.db import init_db as init_db_module


def test_startup_creates_the_tables(client, engine):
    assert {"indexes", "index_assets"} <= set(inspect(engine).get_table_names())


def test_init_db_adds_the_description_column_to_an_older_schema(monkeypatch):
    # Databases created before the description field existed have an
    # `indexes` table without that column; init_db adds it in place.
    legacy_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE indexes (id VARCHAR(36) PRIMARY KEY, name VARCHAR(100) NOT NULL,"
                " user_id VARCHAR(100), created_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            text("INSERT INTO indexes VALUES ('legacy-id', 'Legacy', 'u1', '2026-01-01 00:00:00')")
        )
    monkeypatch.setattr(init_db_module, "engine", legacy_engine)

    init_db_module.init_db()

    columns = {column["name"] for column in inspect(legacy_engine).get_columns("indexes")}
    assert "description" in columns
    with legacy_engine.connect() as connection:
        row = connection.execute(text("SELECT name, description FROM indexes")).one()
    assert tuple(row) == ("Legacy", None)

    # Running it again must not fail on the column that now exists.
    init_db_module.init_db()


def test_init_db_gives_up_after_the_last_attempt(monkeypatch, engine):
    delays = []
    monkeypatch.setattr(init_db_module.time, "sleep", delays.append)
    monkeypatch.setattr(init_db_module, "engine", engine)
    monkeypatch.setattr(
        init_db_module,
        "settings",
        replace(init_db_module.settings, db_init_max_attempts=3, db_init_retry_delay_seconds=0.25),
    )

    def failing_create_all(bind):
        raise OperationalError("SELECT 1", {}, Exception("database is starting"))

    monkeypatch.setattr(init_db_module.Base.metadata, "create_all", failing_create_all)

    with pytest.raises(RuntimeError, match="after 3 attempts"):
        init_db_module.init_db()

    assert delays == [0.25, 0.25]
