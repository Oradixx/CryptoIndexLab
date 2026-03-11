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
    app_name: str = "CryptoIndexLab API2"
    app_version: str = "0.1.0"
    port: int = _get_int_env("PORT", 8002)
    database_url: str = os.getenv(
        "API2_DATABASE_URL",
        "postgresql+psycopg2://crypto_user:crypto_pass@db2:5432/crypto_index",
    )


settings = Settings()
