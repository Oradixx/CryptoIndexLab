from datetime import date

from src.core.symbol_mapping import PROVIDER_SYMBOL_MAPPING


class MarketDataService:
    """Placeholder for future historical market data integration."""

    def resolve_provider_symbol(self, symbol: str) -> str | None:
        return PROVIDER_SYMBOL_MAPPING.get(symbol.upper())

    def get_price_history(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, float]]:
        raise NotImplementedError(
            "Historical market data fetching is not implemented yet."
        )
