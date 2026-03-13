from datetime import UTC, date, datetime

import httpx

from src.core.exceptions import (
    MalformedMarketDataResponseError,
    UpstreamMarketDataError,
    UpstreamMarketDataTimeoutError,
)


class CoinGeckoMarketDataProvider:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        api_key: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._api_key = api_key

    def fetch_daily_prices(
        self,
        provider_symbol: str,
        currency: str,
        days: int,
    ) -> list[tuple[date, float]]:
        request_url = f"{self._base_url}/coins/{provider_symbol}/market_chart"
        query_params = {
            "vs_currency": currency,
            "days": days,
            "interval": "daily",
        }
        headers = self._build_headers()

        try:
            with httpx.Client(timeout=self._timeout_seconds) as http_client:
                response = http_client.get(
                    request_url,
                    params=query_params,
                    headers=headers,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise UpstreamMarketDataTimeoutError(
                "Market data provider timeout while fetching history."
            ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise UpstreamMarketDataError(
                f"Market data provider returned HTTP {status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamMarketDataError(
                "Market data provider request failed."
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise MalformedMarketDataResponseError(
                "Market data provider returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise MalformedMarketDataResponseError(
                "Market data provider returned an unexpected payload."
            )

        raw_prices = payload.get("prices")
        if not isinstance(raw_prices, list):
            raise MalformedMarketDataResponseError(
                "Market data provider response is missing price history."
            )

        prices_by_date: dict[date, float] = {}
        for item in raw_prices:
            if not isinstance(item, list) or len(item) < 2:
                continue

            timestamp_ms, price_value = item[0], item[1]
            if not isinstance(timestamp_ms, (int, float)) or not isinstance(
                price_value, (int, float)
            ):
                continue

            point_date = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).date()
            prices_by_date[point_date] = float(price_value)

        if not prices_by_date:
            raise MalformedMarketDataResponseError(
                "Market data provider returned no usable historical points."
            )

        return sorted(prices_by_date.items(), key=lambda entry: entry[0])

    def _build_headers(self) -> dict[str, str]:
        if not self._api_key:
            return {}

        return {"x-cg-demo-api-key": self._api_key}
