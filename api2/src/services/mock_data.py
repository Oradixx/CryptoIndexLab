from src.models.asset import AvailableAsset

AVAILABLE_ASSETS: tuple[AvailableAsset, ...] = (
    AvailableAsset(symbol="BTC", name="Bitcoin"),
    AvailableAsset(symbol="ETH", name="Ethereum"),
    AvailableAsset(symbol="SOL", name="Solana"),
    AvailableAsset(symbol="ADA", name="Cardano"),
    AvailableAsset(symbol="XRP", name="XRP"),
)
