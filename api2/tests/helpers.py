"""Small helpers shared by the api2 tests."""

ALICE_ID = "user-alice"
BOB_ID = "user-bob"
ALICE_TOKEN = "alice-token"
BOB_TOKEN = "bob-token"

ALICE = {"Authorization": f"Bearer {ALICE_TOKEN}"}
BOB = {"Authorization": f"Bearer {BOB_TOKEN}"}


def index_payload(name="Top 2", assets=(("BTC", 60), ("ETH", 40)), description=None):
    payload = {
        "name": name,
        "assets": [{"symbol": symbol, "weight": weight} for symbol, weight in assets],
    }
    if description is not None:
        payload["description"] = description
    return payload


def create_index(client, headers=ALICE, **kwargs):
    response = client.post("/indexes", json=index_payload(**kwargs), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()
