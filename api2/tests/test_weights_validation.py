"""Validation of index compositions: symbols, individual weights and their total.

The request schema rejects invalid payloads with 422; IndexService repeats
the checks (400 through the API) and is also tested directly below.
"""

import pytest

from helpers import ALICE, index_payload
from src.core.exceptions import DomainValidationError
from src.services.index_service import IndexService


def post_index(client, assets, **kwargs):
    return client.post("/indexes", json=index_payload(assets=assets, **kwargs), headers=ALICE)


def error_messages(response):
    return [error["msg"] for error in response.json()["detail"]]


@pytest.mark.parametrize(
    "assets",
    [
        [("BTC", 100)],
        [("BTC", 50), ("ETH", 50)],
        [("BTC", 0.01), ("ETH", 99.99)],
        # 33.33 + 33.33 + 33.34 is 99.99999999999999 in floating point.
        [("BTC", 33.33), ("ETH", 33.33), ("SOL", 33.34)],
        [("BTC", 30), ("ETH", 20), ("SOL", 15), ("XRP", 10), ("DOGE", 10), ("ADA", 10), ("BNB", 5)],
    ],
    ids=["single-asset", "50-50", "tiny-weight", "float-thirds", "all-seven-assets"],
)
def test_compositions_summing_to_100_are_accepted(client, assets):
    response = post_index(client, assets)

    assert response.status_code == 201, response.text
    assert response.json()["total_weight"] == 100


@pytest.mark.parametrize(
    "assets",
    [
        [("BTC", 60), ("ETH", 30)],
        [("BTC", 60), ("ETH", 50)],
        [("BTC", 99.99)],
        [("BTC", 50), ("ETH", 50.001)],
    ],
    ids=["90", "110", "99.99", "100.001"],
)
def test_total_weight_other_than_100_is_rejected(client, assets):
    response = post_index(client, assets)

    assert response.status_code == 422
    assert error_messages(response) == ["Value error, Total asset weight must equal exactly 100."]


@pytest.mark.parametrize(
    "weight",
    [0, -10, 100.5, "abc", None],
    ids=["zero", "negative", "above-100", "not-a-number", "null"],
)
def test_invalid_individual_weight_is_rejected(client, weight):
    response = client.post(
        "/indexes",
        json={"name": "Bad", "assets": [{"symbol": "BTC", "weight": weight}]},
        headers=ALICE,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "assets",
    [[("BTC", 50), ("BTC", 50)], [("btc", 50), ("BTC", 50)]],
    ids=["same-case", "different-case"],
)
def test_duplicate_symbols_are_rejected(client, assets):
    response = post_index(client, assets)

    assert response.status_code == 422
    assert error_messages(response) == [
        "Value error, Asset symbols must be unique within an index."
    ]


def test_empty_composition_is_rejected(client):
    assert post_index(client, []).status_code == 422


def test_unsupported_symbol_is_rejected(client):
    response = post_index(client, [("BTC", 50), ("XYZ", 50)])

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported asset symbol: XYZ."}


@pytest.mark.parametrize("symbol", ["B", "WAYTOOLONGSYM"], ids=["too-short", "too-long"])
def test_symbol_length_is_checked(client, symbol):
    assert post_index(client, [(symbol, 100)]).status_code == 422


@pytest.mark.parametrize(
    "overrides",
    [{"name": ""}, {"name": "   "}, {"name": "x" * 101}, {"description": "x" * 501}],
    ids=["empty-name", "blank-name", "name-too-long", "description-too-long"],
)
def test_invalid_name_or_description_is_rejected(client, overrides):
    response = client.post("/indexes", json={**index_payload(), **overrides}, headers=ALICE)

    assert response.status_code == 422


def test_invalid_composition_is_also_rejected_on_update(client):
    created = post_index(client, [("BTC", 100)]).json()

    response = client.put(
        f"/indexes/{created['id']}",
        json=index_payload(assets=[("BTC", 50), ("ETH", 40)]),
        headers=ALICE,
    )

    assert response.status_code == 422


@pytest.mark.xfail(
    raises=AssertionError,
    reason="bug: weights are validated before being rounded to 4 decimals for storage",
)
@pytest.mark.parametrize(
    "assets",
    [
        [("BTC", 99.99999), ("ETH", 0.00001)],
        [("BTC", 33.33333), ("ETH", 33.33333), ("SOL", 33.33334)],
    ],
    ids=["weight-rounds-to-zero", "total-rounds-to-99.9999"],
)
def test_an_accepted_composition_still_sums_to_100_once_stored(client, assets):
    response = post_index(client, assets)

    if response.status_code == 201:
        body = response.json()
        assert body["total_weight"] == 100
        assert all(asset["weight"] > 0 for asset in body["assets"])
    else:
        assert response.status_code in (400, 422)


def test_weights_are_stored_with_4_decimals(client):
    response = post_index(client, [("BTC", 50.00004), ("ETH", 49.99996)])

    assert response.status_code == 201
    assert [asset["weight"] for asset in response.json()["assets"]] == [50.0, 50.0]
    assert response.json()["total_weight"] == 100


# --- IndexService checks, without the request schema in front --------------


@pytest.fixture
def index_service(db_session):
    return IndexService(db_session=db_session, market_data_service=None)


@pytest.mark.parametrize(
    ("assets", "message"),
    [
        ([], "At least one asset is required."),
        ([("BTC", 50), ("btc", 50)], "Duplicate asset symbol: BTC."),
        ([("BTC", 50), ("XYZ", 50)], "Unsupported asset symbol: XYZ."),
        ([("BTC", 0), ("ETH", 100)], "Invalid weight for BTC. Use a value between 0 and 100."),
        ([("BTC", 150), ("ETH", -50)], "Invalid weight for BTC. Use a value between 0 and 100."),
        ([("BTC", 60), ("ETH", 30)], "Total asset weight must equal exactly 100."),
    ],
    ids=["empty", "duplicate", "unsupported", "zero-weight", "weight-above-100", "total-90"],
)
def test_index_service_rejects_invalid_compositions(index_service, assets, message):
    with pytest.raises(DomainValidationError) as exc_info:
        index_service.create_index(name="Index", description=None, assets=assets, user_id="u1")

    assert str(exc_info.value) == message


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"name": "   "}, "Index name is required."),
        ({"user_id": "  "}, "Index owner is required."),
        ({"description": "x" * 501}, "Index description must be 500 characters or less."),
    ],
    ids=["blank-name", "blank-owner", "description-too-long"],
)
def test_index_service_rejects_invalid_metadata(index_service, kwargs, message):
    arguments = {"name": "Index", "description": None, "assets": [("BTC", 100)], "user_id": "u1"}

    with pytest.raises(DomainValidationError, match=message):
        index_service.create_index(**{**arguments, **kwargs})
