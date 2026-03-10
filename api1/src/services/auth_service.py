from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
    UnauthorizedError,
)
from src.core.security import SimpleTokenManager, hash_password, verify_password
from src.models.user import User
from src.services.user_repository import UserRepository


class AuthService:
    def __init__(self, db_session: Session, token_manager: SimpleTokenManager) -> None:
        self._db_session = db_session
        self._users = UserRepository(db_session)
        self._token_manager = token_manager

    def register_user(self, email: str, password: str, name: str | None) -> User:
        normalized_email = email.strip().lower()

        password_hash = hash_password(password)

        if self._users.get_by_email(normalized_email):
            raise DuplicateEmailError("Email is already registered.")

        user = self._users.create(
            email=normalized_email,
            hashed_password=password_hash,
            name=name,
        )

        try:
            self._db_session.commit()
        except IntegrityError as exc:
            self._db_session.rollback()
            raise DuplicateEmailError("Email is already registered.") from exc

        self._db_session.refresh(user)
        return user

    def login_user(self, email: str, password: str) -> str:
        user = self._users.get_by_email(email)
        if not user:
            raise InvalidCredentialsError("Invalid credentials.")

        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid credentials.")

        return self._token_manager.issue_token(user.id)

    def get_current_user(self, token: str) -> User:
        user_id = self._token_manager.extract_user_id(token)
        if not user_id:
            raise UnauthorizedError("Unauthorized.")

        user = self._users.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("Unauthorized.")

        return user
