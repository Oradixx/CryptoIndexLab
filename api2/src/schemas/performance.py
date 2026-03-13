from datetime import date

from pydantic import BaseModel, Field


class IndexPerformanceAssetResponse(BaseModel):
    symbol: str = Field(min_length=2, max_length=10)
    name: str = Field(min_length=1, max_length=100)
    weight: float = Field(gt=0)
    normalized_weight: float = Field(gt=0, le=1)


class IndexPerformancePoint(BaseModel):
    date: date
    value: float = Field(ge=0)


class IndexPerformancePeriod(BaseModel):
    start_date: date
    end_date: date
    days: int = Field(ge=1)
    points: int = Field(ge=1)


class IndexPerformanceSummary(BaseModel):
    start_value: float = Field(gt=0)
    end_value: float = Field(ge=0)
    total_return_pct: float


class IndexPerformanceResponse(BaseModel):
    index_id: str
    index_name: str = Field(min_length=1, max_length=100)
    base_value: float = Field(gt=0)
    period: IndexPerformancePeriod
    assets: list[IndexPerformanceAssetResponse] = Field(min_length=1)
    points: list[IndexPerformancePoint] = Field(min_length=1)
    summary: IndexPerformanceSummary
