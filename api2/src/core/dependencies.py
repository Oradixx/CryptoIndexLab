from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.core.exceptions import UnauthorizedRequestError
from src.db.session import get_db_session
from src.services.auth_identity import Api1IdentityService
from src.services.index_performance import IndexPerformanceService
from src.services.index_service import IndexService
from src.services.market_data import MarketDataService

bearer_scheme = HTTPBearer(auto_error=False)


def get_market_data_service(request: Request) -> MarketDataService:
    return request.app.state.market_data_service


def get_identity_service(request: Request) -> Api1IdentityService:
    return request.app.state.identity_service


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    identity_service: Api1IdentityService = Depends(get_identity_service),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        return identity_service.get_user_id_from_token(credentials.credentials)
    except UnauthorizedRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


def get_index_service(
    request: Request,
    db_session: Session = Depends(get_db_session),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> IndexService:
    return IndexService(
        db_session=db_session,
        market_data_service=market_data_service,
    )


def get_index_performance_service(
    request: Request,
    db_session: Session = Depends(get_db_session),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> IndexPerformanceService:
    return IndexPerformanceService(
        db_session=db_session,
        market_data_service=market_data_service,
    )
