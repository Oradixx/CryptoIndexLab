"""Index performance computed on the mock price series.

Every expected value is worked out by hand in mock_market_data.py.
"""

import pytest

from helpers import ALICE, BOB, create_index
from mock_market_data import D1, D2, D3, D4
from src.core.exceptions import (
    MalformedMarketDataResponseError,
    UpstreamMarketDataError,
    UpstreamMarketDataTimeoutError,
)
from src.models.index import CryptoIndex, IndexAsset


def get_performance(client, index_id, headers=ALICE):
    return client.get(f"/indexes/{index_id}/performance", headers=headers)


def series(body):
    return [(point["date"], point["value"]) for point in body["points"]]


def test_performance_of_a_60_40_index(client):
    index = create_index(client, name="60/40", assets=[("BTC", 60), ("ETH", 40)])

    response = get_performance(client, index["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["index_id"] == index["id"]
    assert body["index_name"] == "60/40"
    assert body["base_value"] == 100
    assert series(body) == [
        (D1.isoformat(), pytest.approx(100.0, abs=1e-6)),
        (D2.isoformat(), pytest.approx(102.0, abs=1e-6)),
        (D3.isoformat(), pytest.approx(120.6, abs=1e-6)),
        (D4.isoformat(), pytest.approx(123.06, abs=1e-6)),
    ]
    assert body["summary"] == {
        "start_value": pytest.approx(100.0, abs=1e-6),
        "end_value": pytest.approx(123.06, abs=1e-6),
        "total_return_pct": pytest.approx(23.06, abs=1e-6),
    }
    assert body["period"] == {
        "start_date": D1.isoformat(),
        "end_date": D4.isoformat(),
        "days": 4,
        "points": 4,
    }
    assert body["assets"] == [
        {"symbol": "BTC", "name": "Bitcoin", "weight": 60.0, "normalized_weight": 0.6},
        {"symbol": "ETH", "name": "Ethereum", "weight": 40.0, "normalized_weight": 0.4},
    ]


def test_performance_starts_at_the_first_date_shared_by_all_assets(client):
    # SOL has no price on D1: the series starts on D2 and both assets are
    # rebased on their D2 price.
    index = create_index(client, assets=[("BTC", 50), ("SOL", 50)])

    body = get_performance(client, index["id"]).json()

    assert series(body) == [
        (D2.isoformat(), pytest.approx(100.0, abs=1e-6)),
        (D3.isoformat(), pytest.approx(117.5, abs=1e-6)),
        (D4.isoformat(), pytest.approx(135.5, abs=1e-6)),
    ]
    assert body["period"] == {
        "start_date": D2.isoformat(),
        "end_date": D4.isoformat(),
        "days": 3,
        "points": 3,
    }
    assert body["summary"]["total_return_pct"] == pytest.approx(35.5, abs=1e-6)


def test_performance_of_a_single_asset_index_follows_its_price(client):
    index = create_index(client, assets=[("ETH", 100)])

    body = get_performance(client, index["id"]).json()

    assert [value for _, value in series(body)] == pytest.approx([100, 90, 120, 108], abs=1e-6)
    assert body["summary"]["total_return_pct"] == pytest.approx(8.0, abs=1e-6)


def test_performance_can_be_negative(client, market_provider):
    market_provider.prices["ETH"] = [(D1, 50.0), (D2, 40.0), (D3, 35.0)]
    index = create_index(client, assets=[("ETH", 100)])

    body = get_performance(client, index["id"]).json()

    # 100 * 35 / 50 = 70, so -30 %.
    assert body["summary"] == {
        "start_value": pytest.approx(100.0, abs=1e-6),
        "end_value": pytest.approx(70.0, abs=1e-6),
        "total_return_pct": pytest.approx(-30.0, abs=1e-6),
    }


def test_stored_weights_are_normalized_before_use(client, db_session):
    # Weights 3 and 1 cannot be created through the API (the total must be
    # 100); they are stored directly to check the normalization: 0.75 / 0.25.
    index = CryptoIndex(name="Raw weights", user_id="user-alice")
    index.assets.extend(
        [IndexAsset(symbol="BTC", weight=3.0), IndexAsset(symbol="ETH", weight=1.0)]
    )
    db_session.add(index)
    db_session.commit()

    body = get_performance(client, index.id).json()

    assert [value for _, value in series(body)] == pytest.approx(
        [100.0, 105.0, 120.75, 126.825], abs=1e-6
    )
    assert [asset["normalized_weight"] for asset in body["assets"]] == [0.75, 0.25]


def test_performance_uses_the_updated_composition(client):
    index = create_index(client, assets=[("BTC", 60), ("ETH", 40)])
    client.put(
        f"/indexes/{index['id']}",
        json={"name": "Now ETH only", "assets": [{"symbol": "ETH", "weight": 100}]},
        headers=ALICE,
    )

    body = get_performance(client, index["id"]).json()

    assert body["index_name"] == "Now ETH only"
    assert body["summary"]["end_value"] == pytest.approx(108.0, abs=1e-6)


def test_market_data_is_fetched_once_per_asset_and_then_cached(client, market_provider):
    index = create_index(client, assets=[("BTC", 60), ("ETH", 40)])

    get_performance(client, index["id"])
    get_performance(client, index["id"])

    assert market_provider.calls == [("bitcoin", "usd", 365), ("ethereum", "usd", 365)]


# --- Access -----------------------------------------------------------------


def test_performance_of_another_users_index_is_forbidden(client):
    index = create_index(client)

    response = get_performance(client, index["id"], headers=BOB)

    assert response.status_code == 403
    assert response.json() == {"detail": "You are not allowed to access this index."}


def test_performance_of_an_unknown_index_is_not_found(client):
    response = get_performance(client, "does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Index not found."}


# --- Unusable data ----------------------------------------------------------


@pytest.mark.parametrize(
    ("prices", "detail"),
    [
        (
            {"BTC": [(D1, 100.0)]},
            "Not enough historical data points for BTC.",
        ),
        (
            {"BTC": [(D1, 100.0), (D2, 110.0)], "ETH": [(D3, 60.0), (D4, 54.0)]},
            "Insufficient overlapping historical data across index assets.",
        ),
        (
            {"BTC": [(D1, 100.0), (D2, 110.0)], "ETH": [(D2, 45.0), (D3, 60.0)]},
            "Insufficient overlapping historical data across index assets.",
        ),
        (
            {"BTC": [(D1, 0.0), (D2, 110.0)]},
            "Invalid base price for BTC on 2026-01-01.",
        ),
    ],
    ids=["single-point", "no-common-date", "one-common-date", "zero-base-price"],
)
def test_unusable_price_history_is_a_400(client, market_provider, prices, detail):
    market_provider.prices.update(prices)
    index = create_index(client, assets=[("BTC", 60), ("ETH", 40)])

    response = get_performance(client, index["id"])

    assert response.status_code == 400
    assert response.json() == {"detail": detail}


def test_index_without_assets_is_a_400(client, db_session):
    index = CryptoIndex(name="Empty", user_id="user-alice")
    db_session.add(index)
    db_session.commit()

    response = get_performance(client, index.id)

    assert response.status_code == 400
    assert response.json() == {"detail": "Index has no assets."}


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (UpstreamMarketDataTimeoutError("Market data provider timeout."), 504),
        (UpstreamMarketDataError("Market data provider returned HTTP 429."), 502),
        (MalformedMarketDataResponseError("Market data provider returned invalid JSON."), 502),
    ],
    ids=["timeout", "http-error", "malformed"],
)
def test_market_data_failures_map_to_gateway_errors(client, market_provider, error, status_code):
    index = create_index(client)
    market_provider.error = error

    response = get_performance(client, index["id"])

    assert response.status_code == status_code
    assert response.json() == {"detail": str(error)}
