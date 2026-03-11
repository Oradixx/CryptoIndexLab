from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IndexAsset:
    symbol: str
    name: str
    weight: float


@dataclass
class CryptoIndex:
    id: str
    name: str
    assets: list[IndexAsset]
    owner_user_id: str | None
    created_at: datetime
