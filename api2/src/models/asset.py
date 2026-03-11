from dataclasses import dataclass


@dataclass(frozen=True)
class AvailableAsset:
    symbol: str
    name: str
