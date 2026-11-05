"""CoinGecko provider: request building and response parsing.

Each test answers the provider's HTTP requests with httpx.MockTransport, so
no request leaves the process.
"""

from datetime import UTC, date, datetime

import httpx
import pytest

from src.core.exceptions import (
    MalformedMarketDataResponseError,
    UpstreamMarketDataError,
    UpstreamMarketDataTimeoutError,
)
from src.services.providers.coingecko import CoinGeckoMarketDataProvider

BASE_URL = "https://coingecko.test.invalid/api/v3/"


def ms(year, month, day, hour=0):
    return int(datetime(year, month, day, hour, tzinfo=UTC).timestamp() * 1000)


ONE_POINT = {"prices": [[ms(2026, 1, 1), 1]]}


def fetch(api_key=None):
    provider = CoinGeckoMarketDataProvider(base_url=BASE_URL, timeout_seconds=1, api_key=api_key)
    return provider.fetch_daily_prices(provider_symbol="bitcoin", currency="eur", days=30)


def test_request_targets_the_market_chart_endpoint(mock_http):
    requests = mock_http(lambda request: httpx.Response(200, json=ONE_POINT))

    fetch()

    (request,) = requests
    assert request.method == "GET"
    assert request.url.path == "/api/v3/coins/bitcoin/market_chart"
    assert dict(request.url.params) == {"vs_currency": "eur", "days": "30", "interval": "daily"}
    assert "x-cg-demo-api-key" not in request.headers


def test_api_key_is_sent_when_configured(mock_http):
    requests = mock_http(lambda request: httpx.Response(200, json=ONE_POINT))

    fetch(api_key="demo-key")

    assert requests[0].headers["x-cg-demo-api-key"] == "demo-key"


def test_prices_are_converted_to_one_sorted_point_per_utc_day(mock_http):
    payload = {
        "prices": [
            [ms(2026, 1, 3), 300.0],
            [ms(2026, 1, 1), 100.0],
            [ms(2026, 1, 2), 200],
            # Same UTC day as the previous point: the later entry wins.
            [ms(2026, 1, 2, hour=15), 250.5],
        ]
    }
    mock_http(lambda request: httpx.Response(200, json=payload))

    assert fetch() == [
        (date(2026, 1, 1), 100.0),
        (date(2026, 1, 2), 250.5),
        (date(2026, 1, 3), 300.0),
    ]


def test_malformed_entries_are_skipped(mock_http):
    payload = {
        "prices": [
            "not a list",
            [ms(2026, 1, 1)],
            [ms(2026, 1, 2), "12.5"],
            ["yesterday", 12.5],
            None,
            [ms(2026, 1, 4), 40.0],
        ]
    }
    mock_http(lambda request: httpx.Response(200, json=payload))

    assert fetch() == [(date(2026, 1, 4), 40.0)]


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(200, text="<html>"), "invalid JSON"),
        (httpx.Response(200, json=[1, 2]), "unexpected payload"),
        (httpx.Response(200, json={"market_caps": []}), "missing price history"),
        (httpx.Response(200, json={"prices": "nope"}), "missing price history"),
        (httpx.Response(200, json={"prices": []}), "no usable historical points"),
        (httpx.Response(200, json={"prices": [["x", "y"]]}), "no usable historical points"),
    ],
    ids=["not-json", "not-an-object", "no-prices", "prices-not-a-list", "empty", "all-invalid"],
)
def test_unusable_responses_raise_a_malformed_response_error(mock_http, response, message):
    mock_http(lambda request: response)

    with pytest.raises(MalformedMarketDataResponseError, match=message):
        fetch()


@pytest.mark.parametrize("status_code", [404, 429, 500, 503])
def test_http_errors_raise_an_upstream_error(mock_http, status_code):
    mock_http(lambda request: httpx.Response(status_code, json={"error": "nope"}))

    with pytest.raises(UpstreamMarketDataError, match=f"HTTP {status_code}"):
        fetch()


def test_timeout_raises_a_timeout_error(mock_http):
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    mock_http(handler)

    with pytest.raises(UpstreamMarketDataTimeoutError):
        fetch()


def test_connection_failure_raises_an_upstream_error(mock_http):
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    mock_http(handler)

    with pytest.raises(UpstreamMarketDataError, match="request failed"):
        fetch()


def test_the_test_suite_cannot_reach_the_real_provider():
    # Without mock_http the provider would open a real connection: the
    # network guard from conftest.py stops it before anything is sent.
    with pytest.raises(RuntimeError, match="disabled in tests"):
        fetch()
