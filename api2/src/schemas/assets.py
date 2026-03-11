from pydantic import BaseModel, ConfigDict


class AvailableAssetResponse(BaseModel):
    symbol: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class AvailableAssetsListResponse(BaseModel):
    assets: list[AvailableAssetResponse]
    total: int
