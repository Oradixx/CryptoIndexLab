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
        description: str | None,
        assets: list[tuple[str, float]],
        user_id: str,
    ) -> CryptoIndex:
        normalized_name = self._normalize_index_name(name)
        normalized_description = self._normalize_index_description(description)
        normalized_user_id = self._normalize_user_id(user_id)
        validated_assets = self._validate_assets(assets)
        created_index = CryptoIndex(
            name=normalized_name,
            description=normalized_description,
            user_id=normalized_user_id,
        )
        created_index.assets.extend(validated_assets)

        self._db_session.add(created_index)
        try:
            self._db_session.commit()
        except IntegrityError as exc:
            self._db_session.rollback()
            raise DomainValidationError("Invalid index composition.") from exc

        self._db_session.refresh(created_index)
        return self.get_index(created_index.id, normalized_user_id) or created_index

    def update_index(
        self,
        index_id: str,
        name: str,
        description: str | None,
        assets: list[tuple[str, float]],
        user_id: str,
    ) -> CryptoIndex | None:
        normalized_user_id = self._normalize_user_id(user_id)
        existing_index = self.get_index(index_id=index_id, user_id=normalized_user_id)
        if not existing_index:
            return None

        normalized_name = self._normalize_index_name(name)
        normalized_description = self._normalize_index_description(description)
        validated_assets = self._validate_assets(assets)

        existing_index.name = normalized_name
        existing_index.description = normalized_description
        existing_index.assets.clear()
        self._db_session.flush()
        existing_index.assets.extend(validated_assets)

        try:
            self._db_session.commit()
        except IntegrityError as exc:
            self._db_session.rollback()
            raise DomainValidationError("Invalid index composition.") from exc

        self._db_session.refresh(existing_index)
        return self.get_index(index_id=index_id, user_id=normalized_user_id) or existing_index

    def delete_index(self, index_id: str, user_id: str) -> bool:
        normalized_user_id = self._normalize_user_id(user_id)
        existing_index = self.get_index(index_id=index_id, user_id=normalized_user_id)
        if not existing_index:
            return False

        self._db_session.delete(existing_index)
        self._db_session.commit()
        return True

    def _normalize_user_id(self, user_id: str) -> str:
        normalized_user_id = user_id.strip()
        if not normalized_user_id:
            raise DomainValidationError("Index owner is required.")
        return normalized_user_id

    def _normalize_index_name(self, name: str) -> str:
        normalized_name = name.strip()
        if not normalized_name:
            raise DomainValidationError("Index name is required.")
        return normalized_name

    def _normalize_index_description(self, description: str | None) -> str | None:
        if description is None:
            return None

        normalized_description = description.strip()
        if not normalized_description:
            return None
        if len(normalized_description) > 500:
            raise DomainValidationError("Index description must be 500 characters or less.")
        return normalized_description

    def _validate_assets(self, assets: list[tuple[str, float]]) -> list[IndexAsset]:
        if not assets:
            raise DomainValidationError("At least one asset is required.")

        used_symbols: set[str] = set()
        total_weight = 0.0
        validated_assets: list[IndexAsset] = []

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
            validated_assets.append(
                IndexAsset(
                    symbol=asset.symbol,
                    weight=round(weight, 4),
                )
            )

        if round(total_weight, 4) != 100:
            raise DomainValidationError(
                "Total asset weight must equal exactly 100."
            )

        return validated_assets
