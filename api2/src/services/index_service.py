from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from src.core.exceptions import DomainValidationError
from src.models.asset import AvailableAsset
from src.models.index import CryptoIndex, IndexAsset
from src.services.mock_data import AVAILABLE_ASSETS


class IndexService:
    def __init__(self) -> None:
        self._assets_by_symbol: dict[str, AvailableAsset] = {
            asset.symbol: asset for asset in AVAILABLE_ASSETS
        }
        self._indexes: dict[str, CryptoIndex] = {}
        self._lock = Lock()

    def list_available_assets(self) -> list[AvailableAsset]:
        return list(self._assets_by_symbol.values())

    def list_indexes(self) -> list[CryptoIndex]:
        return list(self._indexes.values())

    def get_index(self, index_id: str) -> CryptoIndex | None:
        return self._indexes.get(index_id)

    def create_index(
        self,
        name: str,
        assets: list[tuple[str, float]],
        owner_user_id: str | None,
    ) -> CryptoIndex:
        normalized_name = name.strip()
        if not normalized_name:
            raise DomainValidationError("Index name is required.")

        if not assets:
            raise DomainValidationError("At least one asset is required.")

        index_assets: list[IndexAsset] = []
        used_symbols: set[str] = set()
        total_weight = 0.0

        for symbol, weight in assets:
            normalized_symbol = symbol.strip().upper()
            if normalized_symbol in used_symbols:
                raise DomainValidationError(f"Duplicate asset symbol: {normalized_symbol}.")

            asset = self._assets_by_symbol.get(normalized_symbol)
            if not asset:
                raise DomainValidationError(f"Unsupported asset symbol: {normalized_symbol}.")

            if weight <= 0 or weight > 100:
                raise DomainValidationError(
                    f"Invalid weight for {normalized_symbol}. Use a value between 0 and 100."
                )

            total_weight += weight
            used_symbols.add(normalized_symbol)
            index_assets.append(
                IndexAsset(
                    symbol=asset.symbol,
                    name=asset.name,
                    weight=round(weight, 4),
                )
            )

        if total_weight > 100:
            raise DomainValidationError("Total asset weight must be <= 100.")

        with self._lock:
            created_index = CryptoIndex(
                id=str(uuid4()),
                name=normalized_name,
                assets=index_assets,
                owner_user_id=owner_user_id,
                created_at=datetime.now(timezone.utc),
            )
            self._indexes[created_index.id] = created_index

        return created_index
