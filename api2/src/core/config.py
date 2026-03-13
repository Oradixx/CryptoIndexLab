import os
from dataclasses import dataclass


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value)
    except ValueError:
        return default


def _get_positive_int_env(name: str, default: int) -> int:
    value = _get_int_env(name, default)
    return value if value > 0 else default


def _get_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        return float(raw_value)
    except ValueError:
        return default


def _get_positive_float_env(name: str, default: float) -> float:
    value = _get_float_env(name, default)
    return value if value > 0 else default


def _get_normalized_env(name: str, default: str) -> str:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip()
    return normalized if normalized else default


def _get_optional_env(name: str) -> str | None:
    raw_value = os.getenv(name)
    if raw_value is None:
        return None

    normalized = raw_value.strip()
    return normalized or None


@dataclass(frozen=True)
class Settings:
    app_name: str = "CryptoIndexLab API2"
    app_version: str = "0.1.0"
    port: int = _get_int_env("PORT", 8002)
    database_url: str = os.getenv(
        "API2_DATABASE_URL",
        "postgresql+psycopg2://crypto_user:crypto_pass@db2:5432/crypto_index",
    )
    market_data_base_url: str = _get_normalized_env(
        "API2_MARKET_DATA_BASE_URL",
        "https://api.coingecko.com/api/v3",
    )
    market_data_timeout_seconds: float = _get_positive_float_env(
        "API2_MARKET_DATA_TIMEOUT_SECONDS",
        10.0,
    )
    market_data_currency: str = _get_normalized_env(
        "API2_MARKET_DATA_CURRENCY",
        "usd",
    ).lower()
    market_data_days: int = _get_positive_int_env("API2_MARKET_DATA_DAYS", 365)
    market_data_cache_ttl_seconds: int = _get_positive_int_env(
        "API2_MARKET_DATA_CACHE_TTL_SECONDS",
        300,
    )
    market_data_api_key: str | None = _get_optional_env("API2_MARKET_DATA_API_KEY")
    auth_api1_me_url: str = _get_normalized_env(
        "API2_AUTH_API1_ME_URL",
        "http://api1:8001/me",
    )
    auth_timeout_seconds: float = _get_positive_float_env(
        "API2_AUTH_TIMEOUT_SECONDS",
        5.0,
    )


settings = Settings()
