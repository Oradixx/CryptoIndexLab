"""Tests for the database initialization run at startup."""

from dataclasses import replace

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

from src.db import init_db as init_db_module


@pytest.fixture
def no_sleep(monkeypatch):
    delays = []
    monkeypatch.setattr(init_db_module.time, "sleep", delays.append)
    return delays


@pytest.fixture
def flaky_create_all(monkeypatch):
    def install(failures):
        state = {"calls": 0}
        real_create_all = init_db_module.Base.metadata.create_all

        def create_all(bind):
            state["calls"] += 1
            if state["calls"] <= failures:
                raise OperationalError("SELECT 1", {}, Exception("database is starting"))
            real_create_all(bind=bind)

        monkeypatch.setattr(init_db_module.Base.metadata, "create_all", create_all)
        return state

    return install


def test_startup_creates_the_users_table(client, engine):
    assert "users" in inspect(engine).get_table_names()


def test_init_db_retries_until_the_database_is_ready(
    monkeypatch, engine, no_sleep, flaky_create_all
):
    monkeypatch.setattr(init_db_module, "engine", engine)
    monkeypatch.setattr(
        init_db_module,
        "settings",
        replace(init_db_module.settings, db_init_max_attempts=3, db_init_retry_delay_seconds=0.5),
    )
    state = flaky_create_all(failures=2)

    init_db_module.init_db()

    assert state["calls"] == 3
    assert no_sleep == [0.5, 0.5]
    assert "users" in inspect(engine).get_table_names()


def test_init_db_gives_up_after_the_last_attempt(monkeypatch, engine, no_sleep, flaky_create_all):
    monkeypatch.setattr(init_db_module, "engine", engine)
    monkeypatch.setattr(
        init_db_module,
        "settings",
        replace(init_db_module.settings, db_init_max_attempts=2, db_init_retry_delay_seconds=0.5),
    )
    state = flaky_create_all(failures=10)

    with pytest.raises(RuntimeError, match="after 2 attempts") as exc_info:
        init_db_module.init_db()

    assert state["calls"] == 2
    assert no_sleep == [0.5]
    assert isinstance(exc_info.value.__cause__, OperationalError)
