from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependencies import get_auth_service, get_current_user
from src.core.exceptions import DuplicateEmailError, InvalidCredentialsError
from src.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from src.services.auth_service import AuthService
from src.services.user_store import UserRecord

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    try:
        user = auth_service.register_user(
            email=str(payload.email),
            password=payload.password,
            name=payload.name,
        )
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        access_token = auth_service.login_user(
            email=str(payload.email),
            password=payload.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: UserRecord = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
