from src.core.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
    UnauthorizedError,
)
from src.core.security import SimpleTokenManager, hash_password, verify_password
from src.services.user_store import InMemoryUserStore, UserRecord


class AuthService:
    def __init__(self, user_store: InMemoryUserStore, token_manager: SimpleTokenManager) -> None:
        self._user_store = user_store
        self._token_manager = token_manager

    def register_user(self, email: str, password: str, name: str | None) -> UserRecord:
        password_hash = hash_password(password)
        try:
            return self._user_store.create_user(email=email, password_hash=password_hash, name=name)
        except ValueError as exc:
            raise DuplicateEmailError("Email is already registered.") from exc

    def login_user(self, email: str, password: str) -> str:
        user = self._user_store.get_by_email(email)
        if not user:
            raise InvalidCredentialsError("Invalid credentials.")

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid credentials.")

        return self._token_manager.issue_token(user.id)

    def get_current_user(self, token: str) -> UserRecord:
        user_id = self._token_manager.extract_user_id(token)
        if not user_id:
            raise UnauthorizedError("Unauthorized.")

        user = self._user_store.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("Unauthorized.")

        return user
