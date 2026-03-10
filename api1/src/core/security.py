import base64
import hashlib
import hmac
import json
import os
import time

PBKDF2_ITERATIONS = 210_000


def _urlsafe_b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_urlsafe_b64encode(salt)}${_urlsafe_b64encode(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_text)
        salt = _urlsafe_b64decode(salt_text)
        expected_digest = _urlsafe_b64decode(digest_text)
    except (TypeError, ValueError):
        return False

    computed_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(computed_digest, expected_digest)


class SimpleTokenManager:
    def __init__(self, secret_key: str, ttl_seconds: int = 3600) -> None:
        self._secret_key = secret_key.encode("utf-8")
        self._ttl_seconds = ttl_seconds

    def issue_token(self, user_id: str) -> str:
        payload = {
            "sub": user_id,
            "exp": int(time.time()) + self._ttl_seconds,
        }
        payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_segment = _urlsafe_b64encode(payload_json)
        signature_segment = _urlsafe_b64encode(self._sign(payload_segment))
        return f"{payload_segment}.{signature_segment}"

    def extract_user_id(self, token: str) -> str | None:
        try:
            payload_segment, signature_segment = token.split(".", 1)
        except ValueError:
            return None

        expected_signature = _urlsafe_b64encode(self._sign(payload_segment))
        if not hmac.compare_digest(signature_segment, expected_signature):
            return None

        try:
            payload_raw = _urlsafe_b64decode(payload_segment)
            payload = json.loads(payload_raw.decode("utf-8"))
            user_id = payload["sub"]
            expires_at = payload["exp"]
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            return None

        if not isinstance(user_id, str) or not isinstance(expires_at, int):
            return None

        if expires_at < int(time.time()):
            return None

        return user_id

    def _sign(self, payload_segment: str) -> bytes:
        return hmac.new(
            self._secret_key,
            payload_segment.encode("utf-8"),
            hashlib.sha256,
        ).digest()
