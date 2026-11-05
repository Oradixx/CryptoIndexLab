"""Test doubles for the two external services api2 depends on."""

from datetime import date

from src.core.exceptions import MalformedMarketDataResponseError, UnauthorizedRequestError
from src.core.symbol_mapping import PROVIDER_SYMBOL_MAPPING

SYMBOL_BY_PROVIDER_ID = {
    provider_id: symbol for symbol, provider_id in PROVIDER_SYMBOL_MAPPING.items()
}


class FakeMarketDataProvider:
    """Stands in for CoinGeckoMarketDataProvider and never touches the network.

    `prices` maps a ticker (BTC, ETH...) to its daily prices. Set `error` to
    make every call raise, as the real provider does on upstream failures.
    """

    def __init__(self, prices: dict[str, list[tuple[date, float]]]) -> None:
        self.prices = {symbol: list(points) for symbol, points in prices.items()}
        self.error: Exception | None = None
        self.calls: list[tuple[str, str, int]] = []

    def fetch_daily_prices(self, provider_symbol: str, currency: str, days: int):
        self.calls.append((provider_symbol, currency, days))
        if self.error is not None:
            raise self.error

        symbol = SYMBOL_BY_PROVIDER_ID[provider_symbol]
        points = self.prices.get(symbol)
        if not points:
            raise MalformedMarketDataResponseError(
                "Market data provider returned no usable historical points."
            )
        return sorted(points)


class FakeIdentityService:
    """Stands in for the call to api1 /me: known tokens map to user ids."""

    def __init__(self, user_id_by_token: dict[str, str]) -> None:
        self._user_id_by_token = user_id_by_token

    def get_user_id_from_token(self, token: str) -> str:
        user_id = self._user_id_by_token.get(token.strip())
        if user_id is None:
            raise UnauthorizedRequestError("Unauthorized.")
        return user_id
