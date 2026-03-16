from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class IndexAssetInput(BaseModel):
    symbol: str = Field(min_length=2, max_length=10)
    weight: float = Field(gt=0, le=100)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Asset symbol is required.")
        return normalized


class CreateIndexRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    assets: list[IndexAssetInput] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Index name is required.")
        return normalized

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_composition(self) -> "CreateIndexRequest":
        symbols = [asset.symbol for asset in self.assets]
        if len(symbols) != len(set(symbols)):
            raise ValueError("Asset symbols must be unique within an index.")

        total_weight = sum(asset.weight for asset in self.assets)
        if total_weight > 100:
            raise ValueError("Total asset weight must be <= 100.")

        return self


class UpdateIndexRequest(CreateIndexRequest):
    pass


class IndexAssetResponse(BaseModel):
    symbol: str
    name: str
    weight: float

    model_config = ConfigDict(from_attributes=True)


class IndexResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    assets: list[IndexAssetResponse]
    total_weight: float
    user_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IndexListResponse(BaseModel):
    indexes: list[IndexResponse]
    total: int
