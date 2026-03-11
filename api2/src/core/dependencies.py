from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.db.session import get_db_session
from src.services.index_service import IndexService
from src.services.market_data import MarketDataService


def get_market_data_service(request: Request) -> MarketDataService:
    return request.app.state.market_data_service


def get_index_service(
    request: Request,
    db_session: Session = Depends(get_db_session),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> IndexService:
    return IndexService(
        db_session=db_session,
        market_data_service=market_data_service,
    )
