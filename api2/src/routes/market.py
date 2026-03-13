from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependencies import get_market_data_service
from src.core.exceptions import (
    MalformedMarketDataResponseError,
    UnsupportedSymbolError,
    UpstreamMarketDataError,
    UpstreamMarketDataTimeoutError,
)
from src.schemas.market import MarketHistoryResponse
from src.services.market_data import MarketDataService

router = APIRouter(tags=["market"])


@router.get("/market/history/{symbol}", response_model=MarketHistoryResponse)
def get_market_history(
    symbol: str,
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> MarketHistoryResponse:
    try:
        return market_data_service.get_price_history(symbol)
    except UnsupportedSymbolError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except UpstreamMarketDataTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    except MalformedMarketDataResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except UpstreamMarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
