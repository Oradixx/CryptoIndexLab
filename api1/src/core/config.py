import os
from dataclasses import dataclass


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_name: str = "CryptoIndexLab API1"
    app_version: str = "0.1.0"
    port: int = _get_int_env("PORT", 8001)
    token_secret: str = os.getenv("API1_JWT_SECRET", "dev-only-change-me")
    token_ttl_seconds: int = _get_int_env("API1_TOKEN_TTL_SECONDS", 3600)
    database_url: str = os.getenv(
        "API1_DATABASE_URL",
        "postgresql+psycopg2://crypto_user:crypto_pass@db1:5432/crypto_auth",
    )


settings = Settings()
