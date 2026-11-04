"""HTTP tests for api1: registration, login and the authenticated /me route."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from helpers import DEFAULT_PASSWORD, TEST_SECRET, bearer, login, register
from src.core.security import SimpleTokenManager, verify_password
from src.models.user import User


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "api1-users-auth", "status": "ok"}


# --- Registration -----------------------------------------------------------


def test_register_creates_a_user_and_hides_the_password(client, db_session):
    response = register(client, email="alice@example.com", name="Alice")

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "name", "created_at"}
    assert body["email"] == "alice@example.com"
    assert body["name"] == "Alice"

    stored = db_session.scalar(select(User).where(User.id == body["id"]))
    assert stored is not None
    assert stored.hashed_password != DEFAULT_PASSWORD
    assert stored.hashed_password.startswith("pbkdf2_sha256$")
    assert verify_password(DEFAULT_PASSWORD, stored.hashed_password)


def test_register_lowercases_the_email(client):
    response = register(client, email="Alice.Smith@Example.COM")

    assert response.status_code == 201
    assert response.json()["email"] == "alice.smith@example.com"


@pytest.mark.parametrize(
    ("name", "expected"),
    [("  Alice  ", "Alice"), ("   ", None), (None, None)],
    ids=["trimmed", "blank-becomes-null", "omitted"],
)
def test_register_normalizes_the_optional_name(client, name, expected):
    response = register(client, name=name)

    assert response.status_code == 201
    assert response.json()["name"] == expected


def test_register_accepts_a_password_of_exactly_8_characters(client):
    assert register(client, password="12345678").status_code == 201


@pytest.mark.parametrize("email", ["alice@example.com", "ALICE@example.com"])
def test_register_rejects_an_email_already_registered(client, alice, email):
    response = register(client, email=email, name="Alice again")

    assert response.status_code == 409
    assert response.json() == {"detail": "Email is already registered."}


def test_duplicate_registration_does_not_create_a_second_user(client, alice, db_session):
    register(client, email="ALICE@EXAMPLE.COM")

    assert len(db_session.scalars(select(User)).all()) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"password": DEFAULT_PASSWORD},
        {"email": "alice@example.com"},
        {"email": "not-an-email", "password": DEFAULT_PASSWORD},
        {"email": "alice@example.com", "password": "1234567"},
        {"email": "alice@example.com", "password": "x" * 129},
        {"email": "alice@example.com", "password": DEFAULT_PASSWORD, "name": ""},
        {"email": "alice@example.com", "password": DEFAULT_PASSWORD, "name": "x" * 101},
    ],
    ids=[
        "missing-email",
        "missing-password",
        "invalid-email",
        "password-too-short",
        "password-too-long",
        "empty-name",
        "name-too-long",
    ],
)
def test_register_rejects_invalid_payloads(client, db_session, payload):
    response = client.post("/register", json=payload)

    assert response.status_code == 422
    assert db_session.scalars(select(User)).all() == []


# --- Login ------------------------------------------------------------------


def test_login_returns_a_bearer_token_for_the_user(client, alice, app):
    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert app.state.token_manager.extract_user_id(body["access_token"]) == alice["id"]


def test_login_is_case_insensitive_on_the_email(client, alice):
    assert login(client, email="ALICE@Example.com").status_code == 200


@pytest.mark.parametrize(
    ("email", "password"),
    [("alice@example.com", "wrong-password"), ("nobody@example.com", DEFAULT_PASSWORD)],
    ids=["wrong-password", "unknown-email"],
)
def test_login_failures_return_the_same_401(client, alice, email, password):
    # Same status and message in both cases: the API does not reveal which
    # emails are registered.
    response = login(client, email=email, password=password)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials."}


def test_login_rejects_an_invalid_payload(client):
    response = client.post("/login", json={"email": "alice@example.com"})

    assert response.status_code == 422


# --- /me and token validation ---------------------------------------------


def test_me_returns_the_current_user(client, alice, alice_token):
    response = client.get("/me", headers=bearer(alice_token))

    assert response.status_code == 200
    assert response.json() == alice


def test_tokens_identify_each_user(client, alice, alice_token):
    bob = register(client, email="bob@example.com", name="Bob").json()
    bob_token = login(client, email="bob@example.com").json()["access_token"]

    assert client.get("/me", headers=bearer(alice_token)).json()["id"] == alice["id"]
    assert client.get("/me", headers=bearer(bob_token)).json()["id"] == bob["id"]


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": ""},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer not-a-token"},
        {"Authorization": "Basic YWxpY2U6c2VjcmV0"},
    ],
    ids=["no-header", "empty-header", "no-token", "garbage-token", "basic-scheme"],
)
def test_me_rejects_missing_or_malformed_credentials(client, alice, headers):
    response = client.get("/me", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized."}


def test_me_rejects_an_expired_token(client, alice):
    expired = SimpleTokenManager(secret_key=TEST_SECRET, ttl_seconds=-1).issue_token(alice["id"])

    assert client.get("/me", headers=bearer(expired)).status_code == 401


def test_me_rejects_a_token_signed_with_another_secret(client, alice):
    forged = SimpleTokenManager(secret_key="attacker-secret").issue_token(alice["id"])

    assert client.get("/me", headers=bearer(forged)).status_code == 401


def test_me_rejects_a_valid_token_for_a_deleted_user(client, alice, alice_token, db_session):
    db_session.delete(db_session.get(User, alice["id"]))
    db_session.commit()

    assert client.get("/me", headers=bearer(alice_token)).status_code == 401


def test_me_rejects_a_token_with_non_ascii_characters(app, alice):
    # HTTP header values are decoded as latin-1, so a client can send any byte.
    with TestClient(app, raise_server_exceptions=False) as raw_client:
        response = raw_client.get("/me", headers={"Authorization": b"Bearer abc.\xe9"})

    assert response.status_code == 401
