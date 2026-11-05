"""HTTP tests for the index CRUD routes of api2, with per-user isolation."""

from datetime import datetime

import pytest
from sqlalchemy import func, select

from helpers import ALICE, ALICE_ID, BOB, create_index, index_payload
from src.models.index import CryptoIndex, IndexAsset


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "api2-crypto-index", "status": "ok"}


def test_available_assets_lists_the_supported_coins(client):
    response = client.get("/assets/available")

    assert response.status_code == 200
    assert response.json() == {
        "assets": [
            {"symbol": "BTC", "name": "Bitcoin"},
            {"symbol": "ETH", "name": "Ethereum"},
            {"symbol": "SOL", "name": "Solana"},
            {"symbol": "XRP", "name": "XRP"},
            {"symbol": "DOGE", "name": "Dogecoin"},
            {"symbol": "ADA", "name": "Cardano"},
            {"symbol": "BNB", "name": "BNB"},
        ],
        "total": 7,
    }


# --- Create -----------------------------------------------------------------


def test_create_index_returns_the_stored_index(client):
    response = client.post(
        "/indexes",
        json=index_payload(
            name="  Blue chips  ",
            description="  Large caps only  ",
            assets=[("btc", 50), ("Eth", 30), (" sol ", 20)],
        ),
        headers=ALICE,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Blue chips"
    assert body["description"] == "Large caps only"
    assert body["user_id"] == ALICE_ID
    assert body["total_weight"] == 100
    assert body["assets"] == [
        {"symbol": "BTC", "name": "Bitcoin", "weight": 50.0},
        {"symbol": "ETH", "name": "Ethereum", "weight": 30.0},
        {"symbol": "SOL", "name": "Solana", "weight": 20.0},
    ]
    datetime.fromisoformat(body["created_at"])


def test_create_index_persists_the_composition(client, db_session):
    created = create_index(client, assets=[("BTC", 70), ("ETH", 30)])

    stored = db_session.get(CryptoIndex, created["id"])
    assert stored.user_id == ALICE_ID
    assert sorted((asset.symbol, asset.weight) for asset in stored.assets) == [
        ("BTC", 70.0),
        ("ETH", 30.0),
    ]


@pytest.mark.parametrize("description", ["   ", None], ids=["blank", "omitted"])
def test_create_index_stores_a_blank_description_as_null(client, description):
    assert create_index(client, description=description)["description"] is None


# --- Read -------------------------------------------------------------------


def test_list_indexes_returns_only_the_callers_indexes(client):
    first = create_index(client, name="Alice 1")
    second = create_index(client, name="Alice 2")
    create_index(client, headers=BOB, name="Bob 1")

    response = client.get("/indexes", headers=ALICE)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["id"] for item in body["indexes"]} == {first["id"], second["id"]}
    assert all(item["user_id"] == ALICE_ID for item in body["indexes"])


def test_list_indexes_is_empty_for_a_new_user(client):
    create_index(client)

    assert client.get("/indexes", headers=BOB).json() == {"indexes": [], "total": 0}


def test_list_indexes_returns_the_newest_first(client, db_session):
    for name, day in [("old", 1), ("newest", 3), ("middle", 2)]:
        index = CryptoIndex(name=name, user_id=ALICE_ID, created_at=datetime(2026, 1, day))
        index.assets.append(IndexAsset(symbol="BTC", weight=100.0))
        db_session.add(index)
    db_session.commit()

    names = [item["name"] for item in client.get("/indexes", headers=ALICE).json()["indexes"]]

    assert names == ["newest", "middle", "old"]


def test_get_index_returns_the_index(client):
    created = create_index(client)

    response = client.get(f"/indexes/{created['id']}", headers=ALICE)

    assert response.status_code == 200
    assert response.json() == created


def test_get_index_of_another_user_is_forbidden(client):
    created = create_index(client)

    response = client.get(f"/indexes/{created['id']}", headers=BOB)

    assert response.status_code == 403
    assert response.json() == {"detail": "You are not allowed to access this index."}


def test_get_unknown_index_is_not_found(client):
    response = client.get("/indexes/does-not-exist", headers=ALICE)

    assert response.status_code == 404
    assert response.json() == {"detail": "Index not found."}


# --- Update -----------------------------------------------------------------


def test_update_index_replaces_name_description_and_composition(client, db_session):
    created = create_index(client, description="v1", assets=[("BTC", 60), ("ETH", 40)])

    response = client.put(
        f"/indexes/{created['id']}",
        json=index_payload(name="Renamed", description="v2", assets=[("SOL", 25), ("ADA", 75)]),
        headers=ALICE,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["name"] == "Renamed"
    assert body["description"] == "v2"
    assert body["created_at"] == created["created_at"]
    assert body["assets"] == [
        {"symbol": "SOL", "name": "Solana", "weight": 25.0},
        {"symbol": "ADA", "name": "Cardano", "weight": 75.0},
    ]
    assert client.get(f"/indexes/{created['id']}", headers=ALICE).json() == body
    # The previous assets are removed, not left behind as orphans.
    assert db_session.scalar(select(func.count()).select_from(IndexAsset)) == 2


def test_update_index_can_keep_the_same_symbols_with_new_weights(client):
    created = create_index(client, assets=[("BTC", 60), ("ETH", 40)])

    response = client.put(
        f"/indexes/{created['id']}",
        json=index_payload(assets=[("ETH", 90), ("BTC", 10)]),
        headers=ALICE,
    )

    assert response.status_code == 200
    weights = {asset["symbol"]: asset["weight"] for asset in response.json()["assets"]}
    assert weights == {"BTC": 10.0, "ETH": 90.0}


def test_update_index_of_another_user_is_forbidden_and_changes_nothing(client):
    created = create_index(client, name="Mine")

    response = client.put(
        f"/indexes/{created['id']}", json=index_payload(name="Hijacked"), headers=BOB
    )

    assert response.status_code == 403
    assert client.get(f"/indexes/{created['id']}", headers=ALICE).json()["name"] == "Mine"


def test_update_unknown_index_is_not_found(client):
    response = client.put("/indexes/does-not-exist", json=index_payload(), headers=ALICE)

    assert response.status_code == 404


def test_update_with_an_invalid_composition_keeps_the_previous_one(client):
    created = create_index(client, assets=[("BTC", 60), ("ETH", 40)])

    response = client.put(
        f"/indexes/{created['id']}",
        json=index_payload(assets=[("BTC", 60), ("ETH", 30)]),
        headers=ALICE,
    )

    assert response.status_code == 422
    assert client.get(f"/indexes/{created['id']}", headers=ALICE).json() == created


# --- Delete -----------------------------------------------------------------


def test_delete_index_removes_it_and_its_assets(client, db_session):
    created = create_index(client)

    response = client.delete(f"/indexes/{created['id']}", headers=ALICE)

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/indexes/{created['id']}", headers=ALICE).status_code == 404
    assert db_session.scalar(select(func.count()).select_from(IndexAsset)) == 0


def test_delete_index_of_another_user_is_forbidden_and_keeps_it(client):
    created = create_index(client)

    assert client.delete(f"/indexes/{created['id']}", headers=BOB).status_code == 403
    assert client.get(f"/indexes/{created['id']}", headers=ALICE).status_code == 200


def test_delete_unknown_index_is_not_found(client):
    assert client.delete("/indexes/does-not-exist", headers=ALICE).status_code == 404


def test_deleting_one_index_leaves_the_others(client):
    kept = create_index(client, name="Kept")
    deleted = create_index(client, name="Deleted")
    bobs = create_index(client, headers=BOB, name="Bob's")

    client.delete(f"/indexes/{deleted['id']}", headers=ALICE)

    assert [item["id"] for item in client.get("/indexes", headers=ALICE).json()["indexes"]] == [
        kept["id"]
    ]
    assert client.get(f"/indexes/{bobs['id']}", headers=BOB).status_code == 200


# --- Authentication ---------------------------------------------------------

PROTECTED_ROUTES = [
    ("GET", "/indexes"),
    ("POST", "/indexes"),
    ("GET", "/indexes/some-id"),
    ("PUT", "/indexes/some-id"),
    ("DELETE", "/indexes/some-id"),
    ("GET", "/indexes/some-id/performance"),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED_ROUTES)
@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer unknown-token"}, {"Authorization": "Basic YWxpY2U6eA=="}],
    ids=["no-token", "unknown-token", "basic-scheme"],
)
def test_index_routes_require_a_valid_bearer_token(client, method, path, headers):
    response = client.request(method, path, headers=headers, json=index_payload())

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized."}


def test_rejected_request_does_not_create_anything(client, db_session):
    client.post("/indexes", json=index_payload(), headers={"Authorization": "Bearer nope"})

    assert db_session.scalar(select(func.count()).select_from(CryptoIndex)) == 0


def test_bob_cannot_see_alices_index_in_any_way(client):
    created = create_index(client)

    assert client.get("/indexes", headers=BOB).json()["total"] == 0
    assert client.get(f"/indexes/{created['id']}", headers=BOB).status_code == 403
    assert client.get(f"/indexes/{created['id']}/performance", headers=BOB).status_code == 403
