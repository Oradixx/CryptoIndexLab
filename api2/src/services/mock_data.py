from src.models.asset import AvailableAsset

AVAILABLE_ASSETS: tuple[AvailableAsset, ...] = (
    AvailableAsset(symbol="BTC", name="Bitcoin"),
    AvailableAsset(symbol="ETH", name="Ethereum"),
    AvailableAsset(symbol="SOL", name="Solana"),
    AvailableAsset(symbol="XRP", name="XRP"),
    AvailableAsset(symbol="DOGE", name="Dogecoin"),
    AvailableAsset(symbol="ADA", name="Cardano"),
    AvailableAsset(symbol="BNB", name="BNB"),
)
