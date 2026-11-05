"""Shared fixtures for the api1 test suite.

Every test runs against its own in-memory SQLite database. The PostgreSQL
engine configured by the application is never used, and outbound network
connections are refused, so the suite needs no running service.
"""

import os
import socket

# The settings are read when `src` is imported, so the environment is set
# first. The URL points to SQLite: even an accidental use of the global
# engine cannot reach a real database.
os.environ["API1_DATABASE_URL"] = "sqlite://"
os.environ["API1_JWT_SECRET"] = "test-secret"
os.environ["API1_TOKEN_TTL_SECONDS"] = "3600"
os.environ["API1_DB_INIT_MAX_ATTEMPTS"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from src.db import init_db as init_db_module  # noqa: E402
from src.db.session import get_db_session  # noqa: E402
from src.main import create_app  # noqa: E402

from helpers import login, register  # noqa: E402


class NetworkAccessBlocked(RuntimeError):
    """Raised when a test tries to open a real network connection."""


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    real_connect = socket.socket.connect

    def guarded_connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise NetworkAccessBlocked(f"Network access is disabled in tests ({address!r}).")
        return real_connect(sock, address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        raise NetworkAccessBlocked(f"DNS resolution is disabled in tests ({host!r}).")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)


@pytest.fixture
def engine():
    # StaticPool keeps one connection, so the in-memory database is shared
    # between the test and the thread that runs the application.
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


@pytest.fixture
def app(engine, session_factory, monkeypatch):
    # The lifespan runs init_db(): point it at the test database so that the
    # real startup code creates the tables.
    monkeypatch.setattr(init_db_module, "engine", engine)

    application = create_app()

    def override_get_db_session():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    application.dependency_overrides[get_db_session] = override_get_db_session
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session(client, session_factory):
    # Depends on `client` so that the tables exist before the test reads them.
    with session_factory() as session:
        yield session


@pytest.fixture
def alice(client):
    response = register(client)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def alice_token(client, alice):
    response = login(client)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]
