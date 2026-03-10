from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.core.exceptions import UnauthorizedError
from src.db.session import get_db_session
from src.models.user import User
from src.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(
    request: Request,
    db_session: Session = Depends(get_db_session),
) -> AuthService:
    token_manager = request.app.state.token_manager
    return AuthService(db_session=db_session, token_manager=token_manager)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        return auth_service.get_current_user(credentials.credentials)
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
