"""Small helpers shared by the api1 tests."""

TEST_SECRET = "test-secret"
DEFAULT_PASSWORD = "correct-horse-42"


def register(client, email="alice@example.com", password=DEFAULT_PASSWORD, name="Alice"):
    payload = {"email": email, "password": password}
    if name is not None:
        payload["name"] = name
    return client.post("/register", json=payload)


def login(client, email="alice@example.com", password=DEFAULT_PASSWORD):
    return client.post("/login", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}
