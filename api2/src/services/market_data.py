from dataclasses import dataclass
from threading import Lock
from time import monotonic

from src.core.config import settings
from src.core.exceptions import UnsupportedSymbolError
from src.core.symbol_mapping import PROVIDER_SYMBOL_MAPPING
from src.schemas.market import MarketHistoryPoint, MarketHistoryRange, MarketHistoryResponse
from src.services.providers.coingecko import CoinGeckoMarketDataProvider


@dataclass
class _MarketHistoryCacheEntry:
    expires_at: float
    response: MarketHistoryResponse


class MarketDataService:
    def __init__(
        self,
        provider: CoinGeckoMarketDataProvider | None = None,
    ) -> None:
        self._provider = provider or CoinGeckoMarketDataProvider(
            base_url=settings.market_data_base_url,
            timeout_seconds=settings.market_data_timeout_seconds,
            api_key=settings.market_data_api_key,
        )
        self._history_days = settings.market_data_days
        self._currency = settings.market_data_currency
        self._cache_ttl_seconds = settings.market_data_cache_ttl_seconds
        self._cache: dict[tuple[str, str, int], _MarketHistoryCacheEntry] = {}
        self._cache_lock = Lock()

    def resolve_provider_symbol(self, symbol: str) -> str | None:
        return PROVIDER_SYMBOL_MAPPING.get(symbol.upper())

    def list_supported_symbols(self) -> list[str]:
        return sorted(PROVIDER_SYMBOL_MAPPING.keys())

    def get_price_history(
        self,
        symbol: str,
    ) -> MarketHistoryResponse:
        normalized_symbol = symbol.strip().upper()
        provider_symbol = self.resolve_provider_symbol(normalized_symbol)
        if not provider_symbol:
            supported_symbols = ", ".join(self.list_supported_symbols())
            raise UnsupportedSymbolError(
                f"Unsupported symbol '{normalized_symbol}'. Supported symbols: {supported_symbols}."
            )

        cache_key = (normalized_symbol, self._currency, self._history_days)
        cached = self._get_cached_response(cache_key)
        if cached is not None:
            return cached

        provider_points = self._provider.fetch_daily_prices(
            provider_symbol=provider_symbol,
            currency=self._currency,
            days=self._history_days,
        )

        points = [
            MarketHistoryPoint(date=point_date, price=price_value)
            for point_date, price_value in provider_points
        ]
        history_range = MarketHistoryRange(
            days=self._history_days,
            start_date=points[0].date,
            end_date=points[-1].date,
        )
        response = MarketHistoryResponse(
            symbol=normalized_symbol,
            currency=self._currency,
            range=history_range,
            points=points,
        )
        self._set_cached_response(cache_key, response)
        return response

    def _get_cached_response(
        self,
        cache_key: tuple[str, str, int],
    ) -> MarketHistoryResponse | None:
        now = monotonic()
        with self._cache_lock:
            cached_entry = self._cache.get(cache_key)
            if not cached_entry:
                return None

            if cached_entry.expires_at <= now:
                del self._cache[cache_key]
                return None

            return cached_entry.response.model_copy(deep=True)

    def _set_cached_response(
        self,
        cache_key: tuple[str, str, int],
        response: MarketHistoryResponse,
    ) -> None:
        expires_at = monotonic() + self._cache_ttl_seconds
        with self._cache_lock:
            self._cache[cache_key] = _MarketHistoryCacheEntry(
                expires_at=expires_at,
                response=response.model_copy(deep=True),
            )
