from datetime import date

from pydantic import BaseModel, Field


class MarketHistoryPoint(BaseModel):
    date: date
    price: float = Field(ge=0)


class MarketHistoryRange(BaseModel):
    days: int = Field(ge=1)
    start_date: date
    end_date: date


class MarketHistoryResponse(BaseModel):
    symbol: str = Field(min_length=2, max_length=10)
    currency: str = Field(min_length=2, max_length=10)
    range: MarketHistoryRange
    points: list[MarketHistoryPoint] = Field(min_length=1)
