from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from src.core.exceptions import DomainValidationError
from src.models.asset import AvailableAsset
from src.models.index import CryptoIndex, IndexAsset
from src.services.market_data import MarketDataService
from src.services.mock_data import AVAILABLE_ASSETS


class IndexService:
    def __init__(self, db_session: Session, market_data_service: MarketDataService) -> None:
        self._db_session = db_session
        self._market_data_service = market_data_service
        self._assets_by_symbol: dict[str, AvailableAsset] = {
            asset.symbol: asset for asset in AVAILABLE_ASSETS
        }

    def list_available_assets(self) -> list[AvailableAsset]:
        return list(self._assets_by_symbol.values())

    def resolve_asset_name(self, symbol: str) -> str:
        asset = self._assets_by_symbol.get(symbol.upper())
        return asset.name if asset else symbol.upper()

    def list_indexes(self, user_id: str) -> list[CryptoIndex]:
        normalized_user_id = user_id.strip()
        stmt = (
            select(CryptoIndex)
            .where(CryptoIndex.user_id == normalized_user_id)
            .options(selectinload(CryptoIndex.assets))
            .order_by(desc(CryptoIndex.created_at))
        )
        return list(self._db_session.scalars(stmt))

    def get_index(self, index_id: str, user_id: str) -> CryptoIndex | None:
        normalized_user_id = user_id.strip()
        stmt = (
            select(CryptoIndex)
            .where(
                CryptoIndex.id == index_id,
                CryptoIndex.user_id == normalized_user_id,
            )
            .options(selectinload(CryptoIndex.assets))
        )
        return self._db_session.scalar(stmt)

    def index_exists(self, index_id: str) -> bool:
        stmt = select(CryptoIndex.id).where(CryptoIndex.id == index_id).limit(1)
        return self._db_session.scalar(stmt) is not None

    def create_index(
        self,
        name: str,
        assets: list[tuple[str, float]],
        user_id: str,
    ) -> CryptoIndex:
        normalized_name = name.strip()
        if not normalized_name:
            raise DomainValidationError("Index name is required.")
        normalized_user_id = user_id.strip()
        if not normalized_user_id:
            raise DomainValidationError("Index owner is required.")

        if not assets:
            raise DomainValidationError("At least one asset is required.")

        used_symbols: set[str] = set()
        total_weight = 0.0

        created_index = CryptoIndex(name=normalized_name, user_id=normalized_user_id)

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
            created_index.assets.append(
                IndexAsset(
                    symbol=asset.symbol,
                    weight=round(weight, 4),
                )
            )

        if total_weight > 100:
            raise DomainValidationError(
                "Total asset weight must be <= 100 for the current policy."
            )

        self._db_session.add(created_index)
        try:
            self._db_session.commit()
        except IntegrityError as exc:
            self._db_session.rollback()
            raise DomainValidationError("Invalid index composition.") from exc

        self._db_session.refresh(created_index)
        return self.get_index(created_index.id, normalized_user_id) or created_index
