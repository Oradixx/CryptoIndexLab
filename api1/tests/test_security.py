"""Unit tests for password hashing and the signed access token.

The token is "JWT-style" rather than a standard JWT: it has two segments,
`base64url(payload).base64url(HMAC-SHA256(secret, payload_segment))`, with no
header segment. The tests below rebuild the expected values with hashlib and
hmac directly, independently of the code under test.
"""

import base64
import hashlib
import hmac
import json

import pytest

from src.core import security
from src.core.security import SimpleTokenManager, hash_password, verify_password

SECRET = "unit-test-secret"
NOW = 1_800_000_000


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def forge_token(payload: dict | str, secret: str = SECRET) -> str:
    """Build a token by hand, the way SimpleTokenManager is expected to."""
    raw = payload if isinstance(payload, str) else json.dumps(payload, separators=(",", ":"))
    payload_segment = b64url(raw.encode("utf-8"))
    signature = hmac.new(secret.encode(), payload_segment.encode(), hashlib.sha256).digest()
    return f"{payload_segment}.{b64url(signature)}"


@pytest.fixture
def frozen_time(monkeypatch):
    clock = {"now": NOW}
    monkeypatch.setattr(security.time, "time", lambda: clock["now"])
    return clock


# --- Password hashing -------------------------------------------------------


def test_hash_password_uses_pbkdf2_sha256_with_a_random_salt():
    password_hash = hash_password("s3cret-password")

    algorithm, iterations, salt, digest = password_hash.split("$")
    assert algorithm == "pbkdf2_sha256"
    assert int(iterations) == 210_000
    assert len(b64url_decode(salt)) == 16
    # The digest is PBKDF2-HMAC-SHA256 of the password with that salt.
    expected = hashlib.pbkdf2_hmac("sha256", b"s3cret-password", b64url_decode(salt), 210_000)
    assert b64url_decode(digest) == expected


def test_hash_password_never_returns_the_same_hash_twice():
    assert hash_password("same-password") != hash_password("same-password")


def test_verify_password_accepts_the_right_password_only():
    password_hash = hash_password("s3cret-password")

    assert verify_password("s3cret-password", password_hash) is True
    assert verify_password("s3cret-passworD", password_hash) is False
    assert verify_password("", password_hash) is False


def test_verify_password_accepts_a_hash_built_independently():
    salt = b"0123456789abcdef"
    digest = hashlib.pbkdf2_hmac("sha256", b"hunter2-hunter2", salt, 1_000)
    stored = f"pbkdf2_sha256$1000${b64url(salt)}${b64url(digest)}"

    assert verify_password("hunter2-hunter2", stored) is True
    assert verify_password("hunter3-hunter3", stored) is False


@pytest.mark.parametrize(
    "stored_hash",
    [
        "",
        "not-a-hash",
        "md5$1000$c2FsdA$ZGlnZXN0",
        "pbkdf2_sha256$not-a-number$c2FsdA$ZGlnZXN0",
        "pbkdf2_sha256$1000$c2FsdA",
    ],
)
def test_verify_password_rejects_malformed_hashes_without_raising(stored_hash):
    assert verify_password("whatever-password", stored_hash) is False


# --- Access token -----------------------------------------------------------


def test_issued_token_matches_the_hand_built_format(frozen_time):
    manager = SimpleTokenManager(secret_key=SECRET, ttl_seconds=3600)

    token = manager.issue_token("user-123")

    assert token == forge_token({"sub": "user-123", "exp": NOW + 3600})
    payload_segment, _ = token.split(".")
    assert json.loads(b64url_decode(payload_segment)) == {"sub": "user-123", "exp": NOW + 3600}


def test_issued_token_round_trips_to_the_user_id(frozen_time):
    manager = SimpleTokenManager(secret_key=SECRET, ttl_seconds=60)

    assert manager.extract_user_id(manager.issue_token("user-123")) == "user-123"


def test_token_is_valid_until_its_expiry_second_then_rejected(frozen_time):
    manager = SimpleTokenManager(secret_key=SECRET, ttl_seconds=60)
    token = manager.issue_token("user-123")

    frozen_time["now"] = NOW + 60
    assert manager.extract_user_id(token) == "user-123"

    frozen_time["now"] = NOW + 61
    assert manager.extract_user_id(token) is None


def test_token_signed_with_another_secret_is_rejected(frozen_time):
    manager = SimpleTokenManager(secret_key=SECRET)
    foreign_token = SimpleTokenManager(secret_key="another-secret").issue_token("user-123")

    assert manager.extract_user_id(foreign_token) is None


def test_token_with_a_tampered_payload_is_rejected(frozen_time):
    manager = SimpleTokenManager(secret_key=SECRET)
    _, signature = manager.issue_token("user-123").split(".")
    tampered_payload = b64url(json.dumps({"sub": "admin", "exp": NOW + 3600}).encode())

    assert manager.extract_user_id(f"{tampered_payload}.{signature}") is None


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "[1, 2, 3]",
        {"exp": NOW + 3600},
        {"sub": "user-123"},
        {"sub": 123, "exp": NOW + 3600},
        {"sub": "user-123", "exp": str(NOW + 3600)},
    ],
    ids=["not-json", "json-list", "no-sub", "no-exp", "sub-not-string", "exp-not-int"],
)
def test_correctly_signed_but_invalid_payload_is_rejected(frozen_time, payload):
    manager = SimpleTokenManager(secret_key=SECRET)

    assert manager.extract_user_id(forge_token(payload)) is None


@pytest.mark.parametrize(
    "token",
    ["", "no-dot-in-token", ".", "a.b.c", "!!!.???"],
)
def test_malformed_token_is_rejected(token):
    assert SimpleTokenManager(secret_key=SECRET).extract_user_id(token) is None


def test_token_with_non_ascii_characters_is_rejected():
    assert SimpleTokenManager(secret_key=SECRET).extract_user_id("abc.é") is None
