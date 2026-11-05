"""Shared fixtures for the api2 test suite.

Every test runs against its own in-memory SQLite database. CoinGecko is
replaced by FakeMarketDataProvider (prices from mock_market_data.py) and the
token check against api1 by FakeIdentityService. Real network connections are
refused, so a test that tries to reach CoinGecko or api1 fails loudly.
"""

import os
import socket

# The settings are read when `src` is imported, so the environment is set
# first. The URLs use the reserved .invalid domain: nothing can answer there.
os.environ["API2_DATABASE_URL"] = "sqlite://"
os.environ["API2_DB_INIT_MAX_ATTEMPTS"] = "1"
os.environ["API2_MARKET_DATA_BASE_URL"] = "http://coingecko.test.invalid/api/v3"
os.environ["API2_MARKET_DATA_API_KEY"] = ""
os.environ["API2_MARKET_DATA_CURRENCY"] = "usd"
os.environ["API2_MARKET_DATA_DAYS"] = "365"
os.environ["API2_MARKET_DATA_CACHE_TTL_SECONDS"] = "300"
os.environ["API2_AUTH_API1_ME_URL"] = "http://api1.test.invalid/me"

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from src.db import init_db as init_db_module  # noqa: E402
from src.db.session import get_db_session  # noqa: E402
from src.main import create_app  # noqa: E402
from src.services.market_data import MarketDataService  # noqa: E402

from fakes import FakeIdentityService, FakeMarketDataProvider  # noqa: E402
from helpers import ALICE_ID, ALICE_TOKEN, BOB_ID, BOB_TOKEN  # noqa: E402
from mock_market_data import MOCK_PRICES  # noqa: E402


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
def market_provider():
    return FakeMarketDataProvider(MOCK_PRICES)


@pytest.fixture
def app(engine, session_factory, market_provider, monkeypatch):
    # The lifespan runs init_db(): point it at the test database so that the
    # real startup code creates the tables.
    monkeypatch.setattr(init_db_module, "engine", engine)

    application = create_app()
    application.state.market_data_service = MarketDataService(provider=market_provider)
    application.state.identity_service = FakeIdentityService(
        {ALICE_TOKEN: ALICE_ID, BOB_TOKEN: BOB_ID}
    )

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
def mock_http(monkeypatch):
    """Route the httpx.Client instances created by the code under test to a handler.

    Returns `install(handler)`; the handler receives each httpx.Request and
    returns an httpx.Response (or raises an httpx error). `install` returns
    the list of requests the handler received.
    """
    real_client = httpx.Client

    def install(handler):
        received: list[httpx.Request] = []

        def recording_handler(request):
            received.append(request)
            return handler(request)

        transport = httpx.MockTransport(recording_handler)

        def client_factory(*args, **kwargs):
            kwargs["transport"] = transport
            return real_client(*args, **kwargs)

        monkeypatch.setattr(httpx, "Client", client_factory)
        return received

    return install
