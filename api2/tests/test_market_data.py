"""Market history route and the in-memory cache of MarketDataService."""

import pytest

from helpers import ALICE
from mock_market_data import D1, D4
from src.core.exceptions import (
    MalformedMarketDataResponseError,
    UnsupportedSymbolError,
    UpstreamMarketDataError,
    UpstreamMarketDataTimeoutError,
)
from src.services import market_data as market_data_module
from src.services.market_data import MarketDataService


def test_market_history_returns_the_daily_prices(client):
    response = client.get("/market/history/btc", headers=ALICE)

    assert response.status_code == 200
    assert response.json() == {
        "symbol": "BTC",
        "currency": "usd",
        "range": {"days": 365, "start_date": D1.isoformat(), "end_date": D4.isoformat()},
        "points": [
            {"date": "2026-01-01", "price": 100.0},
            {"date": "2026-01-02", "price": 110.0},
            {"date": "2026-01-03", "price": 121.0},
            {"date": "2026-01-04", "price": 133.1},
        ],
    }


def test_market_history_rejects_an_unsupported_symbol(client, market_provider):
    response = client.get("/market/history/XYZ", headers=ALICE)

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Unsupported symbol 'XYZ'. Supported symbols: ADA, BNB, BTC, DOGE, ETH, SOL, XRP."
    }
    assert market_provider.calls == []


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (UpstreamMarketDataTimeoutError("timeout"), 504),
        (UpstreamMarketDataError("HTTP 503"), 502),
        (MalformedMarketDataResponseError("invalid JSON"), 502),
    ],
    ids=["timeout", "http-error", "malformed"],
)
def test_market_history_maps_provider_failures(client, market_provider, error, status_code):
    market_provider.error = error

    response = client.get("/market/history/BTC", headers=ALICE)

    assert response.status_code == status_code
    assert response.json() == {"detail": str(error)}


# --- Cache ------------------------------------------------------------------


@pytest.fixture
def clock(monkeypatch):
    state = {"now": 1_000.0}
    monkeypatch.setattr(market_data_module, "monotonic", lambda: state["now"])
    return state


@pytest.fixture
def service(market_provider):
    return MarketDataService(provider=market_provider)


def test_history_is_served_from_the_cache_until_the_ttl_expires(service, market_provider, clock):
    service.get_price_history("BTC")
    clock["now"] += 299
    service.get_price_history("btc")
    assert len(market_provider.calls) == 1

    clock["now"] += 1
    service.get_price_history("BTC")
    assert len(market_provider.calls) == 2


def test_cache_is_per_symbol(service, market_provider, clock):
    service.get_price_history("BTC")
    service.get_price_history("ETH")

    assert [call[0] for call in market_provider.calls] == ["bitcoin", "ethereum"]


def test_cached_history_cannot_be_modified_by_a_caller(service, clock):
    first = service.get_price_history("BTC")
    first.points.clear()

    assert len(service.get_price_history("BTC").points) == 4


def test_failures_are_not_cached(service, market_provider, clock):
    market_provider.error = UpstreamMarketDataError("HTTP 429")
    with pytest.raises(UpstreamMarketDataError):
        service.get_price_history("BTC")

    market_provider.error = None
    assert len(service.get_price_history("BTC").points) == 4


def test_unsupported_symbol_raises_before_calling_the_provider(service, market_provider):
    with pytest.raises(UnsupportedSymbolError):
        service.get_price_history("NOPE")

    assert market_provider.calls == []
