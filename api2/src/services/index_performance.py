from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.core.exceptions import (
    ForbiddenIndexAccessError,
    InsufficientHistoricalDataError,
    InvalidIndexCompositionError,
)
from src.models.asset import AvailableAsset
from src.models.index import CryptoIndex
from src.schemas.performance import (
    IndexPerformanceAssetResponse,
    IndexPerformancePeriod,
    IndexPerformancePoint,
    IndexPerformanceResponse,
    IndexPerformanceSummary,
)
from src.services.market_data import MarketDataService
from src.services.mock_data import AVAILABLE_ASSETS

DEFAULT_BASE_VALUE = 100.0


class IndexPerformanceService:
    def __init__(self, db_session: Session, market_data_service: MarketDataService) -> None:
        self._db_session = db_session
        self._market_data_service = market_data_service
        self._assets_by_symbol: dict[str, AvailableAsset] = {
            asset.symbol: asset for asset in AVAILABLE_ASSETS
        }

    def calculate_index_performance(
        self,
        index_id: str,
        user_id: str,
        base_value: float = DEFAULT_BASE_VALUE,
    ) -> IndexPerformanceResponse | None:
        normalized_user_id = user_id.strip()
        index_obj = self._get_index(index_id=index_id, user_id=normalized_user_id)
        if not index_obj:
            if self._index_exists(index_id):
                raise ForbiddenIndexAccessError("You are not allowed to access this index.")
            return None

        if base_value <= 0:
            raise InvalidIndexCompositionError("Base value must be greater than 0.")
        if not index_obj.assets:
            raise InvalidIndexCompositionError("Index has no assets.")

        weights_by_symbol = self._normalize_weights(index_obj)
        history_by_symbol = self._load_history_by_symbol(weights_by_symbol)
        aligned_dates = self._align_dates(history_by_symbol)

        start_date = aligned_dates[0]
        end_date = aligned_dates[-1]
        base_prices = self._extract_base_prices(start_date, history_by_symbol)

        points: list[IndexPerformancePoint] = []
        for current_date in aligned_dates:
            weighted_ratio = 0.0
            for symbol, normalized_weight in weights_by_symbol.items():
                price_value = history_by_symbol[symbol].get(current_date)
                if price_value is None:
                    raise InsufficientHistoricalDataError(
                        f"Missing aligned price for {symbol} on {current_date.isoformat()}."
                    )

                weighted_ratio += normalized_weight * (price_value / base_prices[symbol])

            points.append(
                IndexPerformancePoint(
                    date=current_date,
                    value=round(base_value * weighted_ratio, 6),
                )
            )

        response_assets: list[IndexPerformanceAssetResponse] = []
        for asset in index_obj.assets:
            symbol = asset.symbol.strip().upper()
            response_assets.append(
                IndexPerformanceAssetResponse(
                    symbol=symbol,
                    name=self._resolve_asset_name(symbol),
                    weight=round(float(asset.weight), 6),
                    normalized_weight=round(weights_by_symbol[symbol], 8),
                )
            )

        start_value = points[0].value
        end_value = points[-1].value
        total_return_pct = 0.0 if start_value == 0 else ((end_value / start_value) - 1) * 100

        return IndexPerformanceResponse(
            index_id=index_obj.id,
            index_name=index_obj.name,
            base_value=round(base_value, 6),
            period=IndexPerformancePeriod(
                start_date=start_date,
                end_date=end_date,
                days=(end_date - start_date).days + 1,
                points=len(points),
            ),
            assets=response_assets,
            points=points,
            summary=IndexPerformanceSummary(
                start_value=round(start_value, 6),
                end_value=round(end_value, 6),
                total_return_pct=round(total_return_pct, 6),
            ),
        )

    def _get_index(self, index_id: str, user_id: str) -> CryptoIndex | None:
        stmt = (
            select(CryptoIndex)
            .where(
                CryptoIndex.id == index_id,
                CryptoIndex.user_id == user_id,
            )
            .options(selectinload(CryptoIndex.assets))
        )
        return self._db_session.scalar(stmt)

    def _index_exists(self, index_id: str) -> bool:
        stmt = select(CryptoIndex.id).where(CryptoIndex.id == index_id).limit(1)
        return self._db_session.scalar(stmt) is not None

    def _normalize_weights(self, index_obj: CryptoIndex) -> dict[str, float]:
        raw_weights: dict[str, float] = {}
        total_weight = 0.0

        for asset in index_obj.assets:
            symbol = asset.symbol.strip().upper()
            weight = float(asset.weight)
            if not symbol:
                raise InvalidIndexCompositionError("Asset symbol is required in index composition.")
            if symbol in raw_weights:
                raise InvalidIndexCompositionError(
                    f"Duplicate asset symbol in index composition: {symbol}."
                )
            if weight <= 0:
                raise InvalidIndexCompositionError(
                    f"Invalid weight for {symbol}. Weights must be greater than 0."
                )

            raw_weights[symbol] = weight
            total_weight += weight

        if total_weight <= 0:
            raise InvalidIndexCompositionError("Total index weight must be greater than 0.")

        return {symbol: weight / total_weight for symbol, weight in raw_weights.items()}

    def _load_history_by_symbol(
        self,
        weights_by_symbol: dict[str, float],
    ) -> dict[str, dict[date, float]]:
        history_by_symbol: dict[str, dict[date, float]] = {}
        for symbol in weights_by_symbol:
            history = self._market_data_service.get_price_history(symbol)
            prices = {point.date: float(point.price) for point in history.points}
            if len(prices) < 2:
                raise InsufficientHistoricalDataError(
                    f"Not enough historical data points for {symbol}."
                )
            history_by_symbol[symbol] = prices

        return history_by_symbol

    def _align_dates(self, history_by_symbol: dict[str, dict[date, float]]) -> list[date]:
        common_dates: set[date] | None = None

        for prices_by_date in history_by_symbol.values():
            symbol_dates = set(prices_by_date.keys())
            common_dates = symbol_dates if common_dates is None else common_dates & symbol_dates

        aligned_dates = sorted(common_dates or [])
        if len(aligned_dates) < 2:
            raise InsufficientHistoricalDataError(
                "Insufficient overlapping historical data across index assets."
            )

        return aligned_dates

    def _extract_base_prices(
        self,
        start_date: date,
        history_by_symbol: dict[str, dict[date, float]],
    ) -> dict[str, float]:
        base_prices: dict[str, float] = {}
        for symbol, prices_by_date in history_by_symbol.items():
            base_price = prices_by_date.get(start_date)
            if base_price is None or base_price <= 0:
                raise InsufficientHistoricalDataError(
                    f"Invalid base price for {symbol} on {start_date.isoformat()}."
                )
            base_prices[symbol] = base_price

        return base_prices

    def _resolve_asset_name(self, symbol: str) -> str:
        asset = self._assets_by_symbol.get(symbol.strip().upper())
        return asset.name if asset else symbol.strip().upper()
